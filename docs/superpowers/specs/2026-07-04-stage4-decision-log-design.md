# Stage 4 — Decision Log & Replay (`gate.db`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 4 ·
[research §8 Q3](../../research/2026-07-03-signal-to-candidate-pipeline.md) (🟢).
Built **with** [Stage 3](2026-07-04-stage3-llm-gate-design.md): same package
(`pipeline/gate/`), same DB (`gate.db`), same spec-pair. No separate registry entry —
the log is written by `main.py gate` and replayed via `main.py gate --replay`.

## Purpose

Make every gate decision **provable, immutable, and replayable**: one append-only row
per candidate reaching the gate, carrying enough pinned state that "the agent never
overrode the math" is a query, not an assertion.

## `gate.db` schema

```sql
gate_runs(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          candidates_snapshot_id INTEGER, decision_count INTEGER,
          tau REAL, model_version TEXT, guardrail_config_version TEXT,
          window TEXT);                       -- 'pre_close' | 'pre_open' | 'adhoc' | 'dry_run'

gate_decisions(
  decision_id  TEXT PRIMARY KEY,              -- injected id_gen seam (uuid4 at runtime)
  run_id       INTEGER NOT NULL REFERENCES gate_runs(id),   -- doubles as trace_id
  decided_at   TEXT NOT NULL,                 -- injected now_iso
  instrument   TEXT NOT NULL, direction TEXT NOT NULL,
  -- input pinning
  input_snapshot_hash TEXT NOT NULL,          -- sha256 of canonical JSON of gate input
  checkpoint   TEXT NOT NULL,                 -- the full serialized input, incl. rendered
                                              -- masked prompt + mask table (JSON)
  -- deterministic recommendation
  det_shares INTEGER NOT NULL, det_stop REAL, det_score REAL,
  size_lo INTEGER NOT NULL, size_hi INTEGER NOT NULL,
  -- agent proposal (NULLs when decision never reached the agent)
  agent_action TEXT, agent_size_mult REAL, agent_confidence REAL,
  agent_rationale TEXT,                       -- STATED reasoning, not verified truth
  agent_error TEXT,                           -- exception type name on API/parse failure
  -- resolution
  tau REAL NOT NULL, final_shares INTEGER NOT NULL,
  delta INTEGER NOT NULL,                     -- final_shares - det_shares (the audit crux)
  clamp_fired INTEGER NOT NULL DEFAULT 0,
  policy_decision TEXT NOT NULL,              -- 'Permit' | 'Deny' | 'DryRun'
  decision_maker TEXT NOT NULL,               -- 'deterministic' | 'agent' | 'human'  (RTS 24)
  -- reproducibility pins
  model_version TEXT, prompt_hash TEXT, guardrail_config_version TEXT NOT NULL);

-- workflow state as first-class, append-only events (event-sourcing)
gate_decision_events(decision_id TEXT NOT NULL REFERENCES gate_decisions(decision_id),
                     seq INTEGER NOT NULL, event TEXT NOT NULL,
                     -- 'created' | 'approved' | 'rejected' | 'heat_cut' | 'replayed'
                     at TEXT NOT NULL, detail TEXT,
                     PRIMARY KEY (decision_id, seq));
```

**Immutability is enforced in the schema, not by convention:**
```sql
CREATE TRIGGER gate_decisions_no_update BEFORE UPDATE ON gate_decisions
BEGIN SELECT RAISE(ABORT, 'gate_decisions is append-only'); END;
CREATE TRIGGER gate_decisions_no_delete BEFORE DELETE ON gate_decisions
BEGIN SELECT RAISE(ABORT, 'gate_decisions is append-only'); END;
```
Same pair on `gate_decision_events`. Consequence: `prune` for `gate.db` deletes **only
old `gate_runs` headers** (default `--keep-days 365`); decisions are the audit trail
and are never cascade-deleted. (If regulation-grade retention ever matters, the DB
file itself is the archive.)

## Field-by-field rationale (research §8 Q3 mapping)

- `decision_maker` — the RTS 24 borrow: which actor decided. `deterministic` when τ
  fall-through / agent failure / dry-run; `agent` when the agent's approve/cut/veto
  stood; `human` reserved for a future manual-override path. Query
  `SELECT count(*) FROM gate_decisions WHERE decision_maker='agent' AND delta > 0`
  must always return 0 — reduce-only, provable.
- `input_snapshot_hash` + `checkpoint` — hash for tamper-evidence and fast diffing;
  checkpoint for actual replay. Canonical JSON = `json.dumps(obj, sort_keys=True,
  separators=(",",":"))` → sha256 (`hashlib`, stdlib).
- `prompt_hash` / `model_version` / `guardrail_config_version` — the three pins that
  make a decision reproducible. `guardrail_config_version` = Stage 2's
  `config_hash()` combined with the gate's own constants (τ, heat cap).
- `agent_rationale` — stored verbatim but labeled *stated* reasoning in the column
  comment and views; >30% of CoT can be post-hoc (research).
- `run_id` serves as `trace_id`: one gate invocation = one trace across its decisions.

## Views (the alerting surface — 🔵 thresholds, calibrate)

- `v_approved_book` — latest run's rows with `final_shares > 0` (what execution reads).
- `v_gate_alerts` — rows from the latest run where `clamp_fired = 1 OR agent_error IS
  NOT NULL OR policy_decision = 'Deny'`.
- `v_delta_history` — per-run veto rate, mean |delta|, clamp-fired count: the drift
  dashboard, and the dataset that later adjudicates whether up-tunes (symmetric band)
  would have added value.
- `v_decision_makers` — decision counts per `decision_maker` per run (the "agent never
  overrode the math" query, materialized as a view).

## Replay

```
uv run python main.py gate --replay <decision_id> [--live]
```
Default (offline): load `checkpoint`, re-run the **deterministic** path — re-render
the masked prompt, recompute `input_snapshot_hash`, re-apply τ/clamp/heat logic to the
*stored* agent proposal — and print a field-by-field diff vs the stored row. Any
mismatch means code drifted from the pinned `guardrail_config_version`; exit non-zero.
`--live` additionally re-asks the (possibly newer) model with the stored prompt and
prints the counterfactual side-by-side — never writes over the original row; appends a
`replayed` event with the diff in `detail`.

Replay of the deterministic path is fully offline → testable in CI like everything
else.

## Testing

Covered within the Stage 3 test files plus dedicated
`tests/test_gate_log.py` / `test_gate_replay.py`: trigger-enforced immutability
(UPDATE/DELETE raise), hash stability across dict ordering, replay-diff detects a
mutated checkpoint, `v_decision_makers` invariant query, event sequence ordering.

## Out of scope / deferred

External alert delivery (the views are the interface; wiring to notifications is
operational, not schema); human-override tooling (`decision_maker='human'` path);
long-term archival policy.
