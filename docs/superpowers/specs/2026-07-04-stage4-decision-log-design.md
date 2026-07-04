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
          window TEXT NOT NULL,               -- 'pre_close'|'pre_open'|'adhoc'|'dry_run'
                                              -- (from Stage 3's --window / dry-run flag)
          -- run-level state the heat check + replay need
          equity REAL NOT NULL, heat_cap REAL NOT NULL, tau REAL NOT NULL,
          model_version TEXT,                  -- resolved model from the API RESPONSE
          guardrail_config_version TEXT NOT NULL);

gate_decisions(
  decision_id  TEXT PRIMARY KEY,              -- injected id_gen seam (uuid4 at runtime)
  run_id       INTEGER NOT NULL REFERENCES gate_runs(id),   -- doubles as trace_id
  decided_at   TEXT NOT NULL,                 -- injected now_iso
  instrument   TEXT NOT NULL, direction TEXT NOT NULL,
  -- input pinning
  input_snapshot_hash TEXT NOT NULL,          -- sha256 of canonical JSON of gate input
  checkpoint   TEXT NOT NULL,                 -- the full serialized per-candidate input,
                                              -- incl. rendered masked prompt + mask entry (JSON)
  -- deterministic recommendation
  det_shares INTEGER NOT NULL, det_stop REAL, det_score REAL, stop_distance REAL,
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
Same pair on `gate_decision_events`.

**`gate.db` is never pruned — at all.** There is no `--keep-days` and `prune` is not
implemented for this DB. An earlier draft pruned `gate_runs` headers; that destroyed
the run-level pins (`window`, `candidates_snapshot_id`, `equity`) that decisions
reference — and headers are tiny, so pruning reclaimed nothing. (SQLite FKs are also
unenforced by `screener_common.connect`, so a header prune would have *silently*
dangled `run_id` rather than erroring.) The DB file itself is the archive.

## Outcome mapping (pinned — every path lands in exactly one row of this table)

| Outcome | policy_decision | decision_maker | final_shares | event |
|---|---|---|---|---|
| Agent approve (conf ≥ τ) | Permit | agent | clamp(size_hi·mult) | approved |
| Agent cut (conf ≥ τ, mult < 1) | Permit | agent | clamp(size_hi·mult) | approved |
| Agent veto (conf ≥ τ) | Permit | agent | 0 | rejected |
| τ fall-through (conf < τ, incl. **discarded veto**) | Permit | deterministic | size_hi | approved |
| Agent error / malformed ×2 | Permit | deterministic | size_hi | approved |
| Heat cut (post-clamp, book-level) | Deny | deterministic | 0 | heat_cut |
| Dry run | DryRun | deterministic | size_hi | created |

Notes: a routine veto is `Permit` (no guardrail fired — the *agent* decided);
`Deny` is reserved for code-level guardrails overriding the flow (heat cap). This
keeps `v_gate_alerts` meaningful — vetoes don't pollute it, discarded vetoes and
heat cuts do.

## Field-by-field rationale (research §8 Q3 mapping)

- `decision_maker` — the RTS 24 borrow: which actor decided the final value. Query
  `SELECT count(*) FROM gate_decisions WHERE decision_maker='agent' AND delta > 0`
  must always return 0 — reduce-only, provable.
- `input_snapshot_hash` + `checkpoint` — hash for tamper-evidence and fast diffing;
  checkpoint for actual replay. Canonical JSON = `json.dumps(obj, sort_keys=True,
  separators=(",",":"), allow_nan=False)` → sha256 (`hashlib`, stdlib). JSON-typed
  columns arriving from `candidates.db` as TEXT (`signals`, `details`) are **parsed
  and re-serialized canonically** before hashing — never hashed as raw stored text —
  at both write and replay time.
- `prompt_hash` / `model_version` / `guardrail_config_version` — the three pins that
  make a decision reproducible. `model_version` comes from the API **response**
  (aliases like `claude-sonnet-5` pin nothing). `guardrail_config_version` = sha256
  of the **effective runtime config** captured at run start — τ, heat_cap, model,
  and Stage 2's `snapshots.config_hash` — so a `--tau 0.7` override changes the hash
  (constants-only hashing would silently lie).
- `agent_rationale` — stored verbatim but labeled *stated* reasoning in views; >30%
  of CoT can be post-hoc (research).
- `run_id` serves as `trace_id`: one gate invocation = one trace across its decisions.

## Views (the alerting surface — 🔵 thresholds, calibrate)

- `v_approved_book` — latest run's rows with `policy_decision = 'Permit' AND
  final_shares > 0` (what execution reads; DryRun and Deny rows are structurally
  excluded — a rehearsal book can never be served).
- `v_gate_alerts` — rows from the latest run where `clamp_fired = 1 OR agent_error
  IS NOT NULL OR policy_decision = 'Deny' OR (agent_action = 'veto' AND
  final_shares > 0)` — the last predicate is the **discarded low-confidence veto**
  (Stage 3 §4's cliff, made visible).
- `v_delta_history` — per-run veto rate, mean |delta|, clamp-fired count, discarded-
  veto count: the drift dashboard, and the dataset that later adjudicates whether
  up-tunes (symmetric band) or honor-all-vetoes would have added value.
- `v_decision_makers` — decision counts per `decision_maker` per run (the "agent never
  overrode the math" query, materialized as a view).

## Replay — the unit is a RUN, not a decision

```
uv run python main.py gate --db gate.db --replay <run_id> [--live]
```
The heat check is book-level: a single decision's `final_shares` can depend on every
sibling in its run, so per-decision replay would systematically false-fail any run
containing a heat cut. Offline replay therefore re-derives the **whole book**: load
the run's header (`equity`, `heat_cap`, `tau`, `guardrail_config_version`) + every
decision's checkpoint, re-render masked prompts, recompute `input_snapshot_hash`,
re-apply τ/clamp/heat logic to the *stored* agent proposals (the LLM is never
re-asked), and print a field-by-field diff vs the stored rows. Any mismatch means
code drifted from the pinned `guardrail_config_version`; exit non-zero.

Default offline replay is **strictly read-only** (CI runs it; the audit DB must not
mutate). `--live` additionally re-asks the (possibly newer) model with each stored
prompt and prints the counterfactual side-by-side — never overwrites the original
rows; appends one `replayed` event per decision with the diff in `detail`.

Replay of the deterministic path is fully offline → testable in CI like everything
else.

## Testing

Covered within the Stage 3 test files plus dedicated
`tests/test_gate_log.py` / `test_gate_replay.py`: trigger-enforced immutability
(UPDATE/DELETE raise), hash stability across dict ordering and across
raw-text-vs-reparsed JSON columns, run-level replay reproduces a heat-cut book
exactly, replay-diff detects a mutated checkpoint, offline replay makes zero writes,
`v_decision_makers` invariant query, outcome-mapping table exercised row by row,
event sequence ordering.

## Out of scope / deferred

External alert delivery (the views are the interface; wiring to notifications is
operational, not schema); human-override tooling (`decision_maker='human'` path);
long-term archival policy.
