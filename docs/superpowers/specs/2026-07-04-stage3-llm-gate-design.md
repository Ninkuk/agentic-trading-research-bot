# Stage 3 — Bounded LLM Gate (`gate`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 3 ·
[research §4, §8 Q2](../../research/2026-07-03-signal-to-candidate-pipeline.md)
(best-evidenced stage, 🟢). Built together with
[Stage 4 — decision log](2026-07-04-stage4-decision-log-design.md); both live in
`pipeline/gate/` and write `gate.db`.

## Purpose

The single place an LLM touches the pipeline: a **reduce-only veto gate** over the
deterministic candidate list. The agent may approve, cut size, or veto — it can
**never increase size, add instruments, or bypass a check**. All guardrails are code,
not prompt (prompt-level guardrails provably fail — 🟢).

## The contract (DOSS pattern, all 🟢)

1. **Read-only state.** The gate reads `candidates.db` (`v_gate_input`); the agent
   receives a rendered, masked view and cannot write anything anywhere.

2. **Masked input at the DATA layer — explicit field whitelist.** The prompt may
   contain, per candidate, **only**:
   - alias (`CAND_A`, `CAND_B`, …), `direction`, `horizon_band`
   - signal names/types and their **normalized** scores (`det_score`, COT premise +
     confirm index values, quality dimension z's)
   - `sector` / `asset_class` label
   - **ATR as % of price** (never absolute price)
   - days-to-earnings as a relative integer ("earnings in 12 days", from
     `next_earnings_date`; omitted when NULL)

   Excluded by construction: ticker, CFTC contract name and market code, absolute
   prices, absolute dates, anything else in `details`. The mask table (real ↔ alias)
   exists only in Python. **Known residual:** sector + metric shape can still
   fingerprint a mega-cap or a flagship ETF — data-layer masking reduces memorized-
   ticker bias, it cannot eliminate it; that limit is accepted and documented rather
   than papered over. The leak regression test (below) enforces the whitelist.

3. **Fixed output grammar.** The agent must emit exactly one JSON object per candidate:
   ```json
   {"action": "approve" | "veto",
    "size_mult": 0.0-1.0,
    "confidence": 0.0-1.0,
    "rationale": "<= 500 chars"}
   ```
   Parsed with `json.loads` + strict schema/range validation in code. Anything else —
   extra keys, out-of-range numbers, prose — is a **malformed response** (see failure
   policy).

4. **Confidence threshold τ** (abstention rule):
   ```
   if confidence < TAU:          final = deterministic recommendation (full size_hi)
   elif action == "veto":        final = 0
   else:                         final = clamp(size_hi * size_mult, size_lo, size_hi)
   ```
   `TAU = 0.5` default — an open calibration question for slow composite signals
   (research §8); a `catalog.py` constant, hash-pinned per decision.

   **Stated consequence (pinned deliberately):** a *low-confidence veto is
   discarded* — veto @ confidence 0.51 → 0 shares, veto @ 0.49 → full size. This is
   the research formula taken literally (`final = deterministic_default if
   confidence < τ`), and it is intentional: τ exists so noisy caution cannot de-lever
   the trusted deterministic book. The cliff is a calibration risk, so every
   discarded veto is (a) logged with `decision_maker='deterministic'` and (b)
   surfaced by `v_gate_alerts` (`agent_action='veto' AND final_shares > 0`). If the
   Stage 4 delta history shows discarded vetoes would have dodged losses, the rule
   graduates to "vetoes honored regardless of confidence" as a config change.

5. **Clamp in code.** `size_mult` outside [0,1] or any attempt to exceed `size_hi`
   sets `clamp_fired = 1` — itself a risk alert (Stage 4 view).

6. **Portfolio heat check runs AFTER the clamp**, in Python, over the whole approved
   book. Per-position contribution = `final_shares × stop_distance` (the *realized*
   risk — not Stage 2's theoretical `risk_dollars`, which overstates risk when the
   ADV cap binds). Equity = the candidates snapshot's `equity` column. If the sum
   exceeds `heat_cap` (default 6% of equity), **whole positions are zeroed in
   ascending `(det_score, instrument)` order until the book fits** — no partial
   shaves in v1. A zeroed position gets `policy_decision='Deny'`,
   `final_shares = 0`, event `heat_cut`. The agent has no path around this — it runs
   downstream of everything the agent says.

## Failure policy (pinned)

API error after bounded retries, or malformed response twice for a candidate →
**fall through to the deterministic recommendation** (`decision_maker =
'deterministic'`, `agent_error` = exception type name). Rationale: the deterministic
pipeline is the trusted baseline; the LLM only adds caution on top. A broken agent
must not be able to halt the system (availability) nor force trades beyond the
deterministic book (it can't — reduce-only). The skipped check is surfaced via
`v_gate_alerts` because a landmine check that silently didn't happen is itself
alert-worthy.

## LLM call mechanics (stdlib-only)

- `pipeline/gate/llm.py`: `complete(system, user, *, model, api_key, post=_post) -> dict`
  where `_post` wraps `urllib.request` (JSON POST to
  `https://api.anthropic.com/v1/messages`, headers `x-api-key`,
  `anthropic-version: 2023-06-01`), with its own retry loop reusing
  `http_client.retry_delay` for backoff. Tests inject a fake `post` — **no network in
  tests**, same seam discipline as every fetcher.
- `ANTHROPIC_API_KEY` from the environment (`.env` convention). **Secret hygiene:** on
  HTTP errors print `type(e).__name__` only — the URL/body must never leak (the body
  contains the masked prompt; the header contains the key).
- Model: `claude-sonnet-5` default, `--model` overridable. **The reproducibility pin
  `model_version` is taken from the API *response* body's `model` field**, not the
  request — request ids are aliases whose server-side resolution can change; the
  response records what actually served the decision. `prompt_hash` = sha256 of the
  exact rendered prompt. `temperature 0`, `max_tokens` small (the grammar is tiny by
  design).
- One API call per candidate (independent decisions, cleaner audit rows, trivial
  retries). Selective consensus (N calls, agreement-weighted) is a documented post-v1
  hardening (research §4).

## What the agent is FOR (prompt scope)

The system prompt frames the only jobs the evidence supports: sanity-read the masked
quantitative picture for red flags (deteriorating confirm leg, crowded positioning,
imminent binary event given "earnings in N days") and express **caution** — never
conviction. It is told the output grammar and that vetoes/cuts are logged and audited.
No news retrieval, no tools, no memory in v1: inputs are exactly the whitelisted
masked facts. (Evidence: LLM discretionary alpha ≈ 0 🟢; expressing caution is the
only asymmetric payoff available to a reduce-only gate.)

## Execution windows

Designed to be invoked by Stage 5 at **pre-close** (and optionally pre-open) on
trading days — but the gate itself is window-agnostic: it processes whatever the
latest candidates snapshot is when invoked. Window policy lives in Stage 5; the
invocation labels itself via `--window` (recorded in `gate_runs.window`).

## Output

`gate.db` — schema owned by Stage 4 (decision log). The gate writes one immutable
`gate_decisions` row per candidate + a `gate_runs` header; the final approved book is
readable via `v_approved_book` (Stage 4 views; `policy_decision='Permit'` rows only,
so a dry-run or Deny row can never be served to execution). Nothing else consumes the
LLM's words: downstream (execution, out of scope) reads `final_shares` from the log.

## CLI

```
uv run python main.py gate --db gate.db --candidates-db candidates.db \
  [--tau 0.5] [--model claude-sonnet-5] [--window pre_close] [--dry-run]
```
`run(db_path, candidates_db, tau=TAU, model=DEFAULT_MODEL, api_key=None,
complete=llm.complete, window="adhoc", dry_run=False, connect_ro=..., now_iso=None,
id_gen=None, only=None)` — `id_gen` (default `uuid.uuid4`) is the injected
decision-id seam so tests are deterministic; `only` filters candidates by instrument.
There is **no `--keep-days`**: `gate.db` is the audit trail and is never pruned
(Stage 4).

`--dry-run`: full pipeline, masked prompts rendered and logged, no API call, decisions
written with `decision_maker='deterministic'`, `policy_decision='DryRun'` — the
rehearsal mode for testing prompts and the replay harness. DryRun rows are excluded
from `v_approved_book` by construction.

## Testing

`tests/test_gate_{catalog,llm,db_schema,db_write,db_views,run}.py` + registry entry.
Fake `complete` returning canned JSON exercises: τ fall-through, honored veto,
**discarded low-confidence veto (alert row asserted)**, cut, clamp firing
(size_mult 1.7), malformed→deterministic fallback, heat-cut ordering incl. the
`(det_score, instrument)` tie-break, dry-run exclusion from `v_approved_book`, and the
**whitelist leak test**: rendered prompts must contain no ticker, no CFTC contract
name or market code, and no absolute price from the fixture set.

## Out of scope / deferred

Symmetric ±15% band (documented future experiment, gated on Stage 4 logged deltas
showing up-tunes would have added value); selective consensus; news/tool access;
execution.
