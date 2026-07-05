# Claude Roadmap (Claude-invoked commands)

Parent tracker for the **Claude command layer**: on-demand tasks where Claude
Code is the executor, invoked by the user — not scheduled, not part of the
deterministic pipeline. These commands live exactly at the two boundaries the
pipeline deliberately refuses to cross: talking to the live brokerage
(sources → pipeline → **execution**) and narrating machine ledgers for a
human. Same status legend as [PIPELINE_ROADMAP.md](PIPELINE_ROADMAP.md);
"Built" here means the command exists as a project skill/slash command in
`.claude/` and has been exercised end-to-end.

## Guiding invariant

Claude commands may **read** anything and may fetch live account state, but
whatever they learn enters the system **as data, not as live calls**: account
snapshots land in their own SQLite DB (structurally a screener —
fetch/db/run/catalog) so downstream consumers stay offline-testable and
Stage 4's replay stays deterministic. No pipeline stage ever calls a
brokerage API or an LLM outside the Stage 3 gate; Claude commands are the
human-triggered exception, and they write through the same door all data
enters.

## Commands

### `account-positions` — resolve account positions/details 💡

Origin: 2026-07-05 session — Stage 2/3 review found the account-awareness
blind spots. When invoked, Claude resolves the live account via the
Robinhood MCP (positions, equity, cash, buying power) and snapshots it into
`portfolio.db`:

- `positions` (snapshot-scoped): instrument, shares, cost basis, market value.
- `account` (snapshot-scoped): equity, cash, buying power — replaces the
  static `PIPELINE_EQUITY` env var, which goes stale between manual updates.

Downstream integrations the snapshot unlocks (each its own follow-on,
likely in promote's GateConfig):

1. **Dedup vs holdings** — today the funnel re-recommends an instrument the
   account already holds (e.g. GLD two days running while the COT extreme
   persists).
2. **G5 counts real exposure** — sector cap currently sees only the cohort;
   existing positions in a sector are invisible.
3. **Whole-book heat** — Stage 3's 6% heat cap covers only the current run's
   book; risk in already-open positions is uncounted.
4. **Marked-to-market equity** — sizing tracks the account instead of the
   last `.env` edit.

Design questions for the spec: `portfolio.db` schema ownership (a normal
screener package the command shells into vs. Claude writing SQL directly —
prefer the former); how stop distances for *held* positions enter the heat
calculation; secret hygiene for MCP errors.

### `paper-trail-report` — humanify the error logs & decision ledgers 💡

When invoked, Claude reads every failure surface and produces a
plain-English digest a human can act on, instead of raw rows:

- `candidates.db` — `rejections` / `v_rejection_summary` (which gate killed
  what, and why).
- `gate.db` — `v_gate_alerts` (clamps, agent errors, discarded vetoes),
  `v_delta_history` (is the agent getting noisier?), `v_decision_makers`.
- `schedule.db` — `v_failures` (jobs whose last attempt errored out),
  `v_recent_runs`.
- `schedule.log` — the skip-and-continue stderr warnings (e.g. a leads leg
  that silently sat out a run).

Output shape (sketch): "yesterday's pre-close run promoted 4 of 19 leads;
14 died at the direction gate (shorts, expected), 1 at liquidity (UNG fell
under the $10M floor); the gate vetoed nothing but one veto was discarded
below τ — third time this week, consider reviewing τ." Read-only by
design — this command never mutates any DB.

### `gate-llm-backend` — headless Claude serves the Stage 3 gate 💡

Origin: 2026-07-05 decision — **strictly no `ANTHROPIC_API_KEY`** in this
project. The Stage 3 gate's LLM call moves off the raw `api.anthropic.com`
path onto subscription-authenticated headless Claude Code:
`claude -p --output-format json --model <model>`, invoked via stdlib
`subprocess` (an external binary, same standing as `git` in
`trials --register`).

The one exception to this roadmap's "user-invoked" rule: this command is
invoked *by the pipeline* (gate run / scheduler window), and ships as code
in `pipeline/gate/`, not as a skill — "Built" here means the backend flag
exists, is the default, and passes offline tests with a faked subprocess.

Sketch:

- `complete_cli()` in `pipeline/gate/llm.py` behind the existing injected
  `complete=` seam — same `(system, user, model)` in, same body shape out,
  so `response_text` / `response_model` / `parse_agent` and every guardrail
  downstream stay untouched. Tests keep faking the seam; nothing spawns a
  real subprocess offline.
- `--backend {claude-cli, api}` on `main.py gate`, default `claude-cli`
  (the no-key decision is policy, not preference); `api` kept for
  compatibility. `_resolve_api_key` becomes backend-aware — the CLI path
  must not demand a key.
- `model_version` pin comes from the CLI's JSON output (it reports the
  serving model), keeping the Stage 4 reproducibility contract.

Accepted trade-offs (recorded so the spec doesn't relitigate): no
`temperature=0` control via the CLI — rationales may vary run-to-run;
bounds are unaffected (resolve.py clamps regardless, and replay re-derives
from the *stored* proposal, so determinism-of-audit survives). Cron must
run as the logged-in user with `claude` on PATH. `--dry-run` remains
zero-backend.

Design questions for the spec: subprocess timeout + retry mapping onto
`LLM_ATTEMPTS`; how scheduler `argv_for` passes `--backend`; prompt
delivery via stdin (argv leaks into `ps` output — the masked prompt is not
secret, but the habit matters); parsing the CLI JSON envelope vs. the
Messages body shape.

## Future ideas

Order placement (Claude walks the user through executing `v_approved_book`,
one confirmation per order) — deliberately unscoped until the pipeline has
run live for a while and the paper trail has been audited.
