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
2. **Masked input at the DATA layer.** Tickers → `CAND_A`, `CAND_B`…; absolute dates →
   relative offsets ("earnings in 12 days"); `as_of` dates dropped. Sector names,
   signal metrics, scores, and horizon bands pass through. The mask table
   (real ↔ alias) exists only in Python. "Pretend you don't know the ticker" is never
   relied on — the model simply isn't shown it.
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
5. **Clamp in code.** `size_mult` outside [0,1] or any attempt to exceed `size_hi`
   sets `clamp_fired = 1` — itself a risk alert (Stage 4 view).
6. **Portfolio heat check runs AFTER the clamp**, in Python, over the whole approved
   book: if Σ `risk_dollars` (scaled by final/recommended shares) > `heat_cap`
   (default 6% of equity), lowest-`det_score` positions are cut to fit and the check
   is recorded as `policy_decision = Deny` on the cut rows. The agent has no path
   around this — it runs downstream of everything the agent says.

## Failure policy (pinned)

API error after bounded retries, or malformed response twice for a candidate →
**fall through to the deterministic recommendation** (`decision_maker =
'deterministic'`, `agent_error` recorded). Rationale: the deterministic pipeline is
the trusted baseline; the LLM only adds caution on top. A broken agent must not be
able to halt the system (availability) nor force trades beyond the deterministic book
(it can't — reduce-only). The skipped-veto is surfaced via the `v_gate_alerts` view
because a landmine check that silently didn't happen is itself alert-worthy.

## LLM call mechanics (stdlib-only)

- `pipeline/gate/llm.py`: `complete(system, user, *, model, api_key, post=_post) -> str`
  where `_post` wraps `urllib.request` (JSON POST to
  `https://api.anthropic.com/v1/messages`, headers `x-api-key`,
  `anthropic-version: 2023-06-01`), reusing `http_client.retry_delay` for backoff.
  Tests inject a fake `post` — **no network in tests**, same seam discipline as every
  fetcher.
- `ANTHROPIC_API_KEY` from the environment (`.env` convention). **Secret hygiene:** on
  HTTP errors print `type(e).__name__` only — the URL/body must never leak (the body
  contains the masked prompt; the header contains the key).
- Model: `claude-sonnet-5` default, `--model` overridable; `model_version` +
  `prompt_hash` (sha256 of the exact rendered prompt) are recorded per decision
  (Stage 4). `temperature 0`, `max_tokens` small (the grammar is tiny by design).
- One API call per candidate (independent decisions, cleaner audit rows, trivial
  retries). Selective consensus (N calls, agreement-weighted) is a documented post-v1
  hardening (research §4).

## What the agent is FOR (prompt scope)

The system prompt frames the only jobs the evidence supports: sanity-read the masked
quantitative picture for red flags (deteriorating confirm leg, crowded positioning,
imminent binary event given "earnings in N days") and express **caution** — never
conviction. It is told the output grammar and that vetoes/cuts are logged and audited.
No news retrieval, no tools, no memory in v1: inputs are exactly the masked candidate
facts. (Evidence: LLM discretionary alpha ≈ 0 🟢; expressing caution is the only
asymmetric payoff available to a reduce-only gate.)

## Execution windows

Designed to be invoked by Stage 5 at **pre-close** (and optionally pre-open) on
trading days — but the gate itself is window-agnostic: it processes whatever the
latest candidates snapshot is when invoked. Window policy lives in Stage 5, not here.

## Output

`gate.db` — schema owned by Stage 4 (decision log). The gate writes one immutable
`gate_decisions` row per candidate + a `gate_runs` header; the final approved book is
readable via `v_approved_book` (Stage 4 views). Nothing else consumes the LLM's words:
downstream (execution, out of scope) reads `final_shares` from the log.

## CLI

```
uv run python main.py gate --db gate.db --candidates-db candidates.db \
  [--tau 0.5] [--model claude-sonnet-5] [--dry-run] [--keep-days 365]
```
`run(db_path, candidates_db, tau=TAU, model=DEFAULT_MODEL, api_key=None,
complete=llm.complete, keep_days=None, connect_ro=..., now_iso=None, ids=None)`.
`--dry-run`: full pipeline, masked prompts rendered and logged, no API call, decisions
written with `decision_maker='deterministic'`, `policy_decision='DryRun'` — the
rehearsal mode for testing prompts and the replay harness.

## Testing

`tests/test_gate_{catalog,llm,db_schema,db_write,db_views,run}.py` + registry entry.
Fake `complete` returning canned JSON exercises: τ fall-through, veto, cut, clamp
firing (size_mult 1.7), malformed→deterministic fallback, heat-cap cut ordering,
masking (assert no real ticker appears in any rendered prompt — a regression test on
the leak surface).

## Out of scope / deferred

Symmetric ±15% band (documented future experiment, gated on Stage 4 logged deltas
showing up-tunes would have added value); selective consensus; news/tool access;
execution.
