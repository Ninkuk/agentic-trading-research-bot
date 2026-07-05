# Defenses Roadmap (post-v1 pipeline hardening)

Parent tracker for defenses layered onto the **built** pipeline — items that
close identified risk gaps rather than add new signal legs. Kept separate so
[PIPELINE_ROADMAP.md](PIPELINE_ROADMAP.md) stays a finished v1 record. Same
status legend and `registry.py`/`GateConfig` source-of-truth conventions.

## Fractional sizing + notional-cost check (small-account support) ✅

Origin: first live funnel run, 2026-07-05 — real equity $200.37 in the
risk-off regime (scalar 0.5) leaves a $1.00 risk budget per trade, and
`size_candidate`'s `math.floor()` (`pipeline/promote/gates.py`) rounds
every position to 0 shares. All four surviving ETF leads died `size_zero`.
The account is structurally locked out of whole-share trading; Robinhood
cash accounts support fractional equity orders, so the lockout is
self-imposed.

Two coupled changes (the second is a genuine risk gap the first exposes):

1. **Fractional shares** behind a GateConfig flag (e.g.
   `fractional_shares: bool`, off by default so config_hash pins the
   switch). `shares` becomes REAL end-to-end: candidates schema,
   `v_gate_input`, the gate's `size_lo`/`size_hi`, resolve's
   `floor(size_hi * mult)` clamp, ledger columns, replay. Participation
   cap semantics unchanged (a fractional share is always under 1% of ADV).
2. **Notional-cost check** — `size_candidate` never verifies
   `shares × price ≤ available cash` (or an aggregate-notional cap across
   the cohort). Moot while floor() zeros everything; a real overdraft gap
   once sizes go fractional (and latent even for whole shares on a small
   account: 1 GLD share ≈ $310 > $200 equity would have passed today's
   sizing if the risk budget had allowed it).

Built 2026-07-05. Design questions resolved:

- **Rounding**: floor to 1e-6 (Robinhood's increment); `min_notional: 1.0`
  in GateConfig rejects dust below the $1 per-order minimum (`gate='notional'`).
- **Flag plumbing**: `GateConfig.fractional_shares` (off by default), flipped
  by `promote --fractional` or the `PIPELINE_FRACTIONAL` env (the scheduler
  path — same pattern as `PIPELINE_EQUITY`); config_hash pins the switch.
  The quantum then travels **with the data**: snapshots.fractional →
  `v_gate_input` → `gate_runs.fractional`, so Stage 4 replay re-derives with
  the stored quantum, never live config.
- **Migration stance**: `ALTER TABLE ... ADD COLUMN` for the two non-append-only
  headers (snapshots, gate_runs); share columns' DDL is REAL for fresh DBs and
  old INTEGER-affinity DBs store non-integral REALs losslessly (pinned by test).
  `gate_decisions` needed no ALTER.
- **Notional-cost check** (both modes, not just fractional): per-candidate
  clamp `shares ≤ equity/price` at sizing, plus a cohort-level
  `gate_notional_book` cut (ascending det_score, mirroring heat_cut) so the
  book's total notional fits inside equity. Equity is the cash proxy until
  `portfolio.db` (CLAUDE_ROADMAP `account-positions`) supplies real cash.
- **`heat_cut`**: unchanged — already REAL-safe (no flooring), still cuts
  whole positions.
- **Deferred**: per-symbol fractional eligibility (no data source yet); a
  post-gate agent cut can land under $1 notional — order placement (a Claude
  command) must skip dust orders.

## Crowding / pump defense ✅

Origin: 2026-07-05 session — gap analysis of the anonymized LLM gate. The
funnel is pump-resistant by construction (lead signals are price-blind; G3
floors kill the microcap pump habitat; ATR sizing auto-shrinks as hype
inflates volatility), but one case is uncovered: **a large-cap quality lead
undergoing a meme episode** — buying a sound company at a crowd-inflated
price. The purpose-built input already exists unused: `reddit.db`
(ApeWisdom; per-ticker mentions, upvotes, rank, 24h deltas, `v_history`
time series).

Two tiers, mirroring the system's code-vs-LLM split:

### Tier 1 — deterministic crowding gate in `pipeline/promote/` ✅

- New gate after G3 (promote already attaches market context there:
  liquidity from stocks/etfs.db, crowding from reddit.db — same move,
  third read-only DB).
- Kill when attention is extreme **relative to the name's own baseline**
  (e.g. mention rank ≤ N *and* mentions ≥ X× its trailing norm). Absolute
  mentions cannot work — SPY/QQQ are always chattered about; the measure
  must be per-name (`v_history` window functions).
- Top-N list semantics: absence from reddit.db = calm = pass free (no
  data_missing noise).
- Every kill logged `gate='crowding'`; thresholds join the frozen
  GateConfig (visible in config_hash), calibrated via Stage 6 trials.

### Tier 2 — masked crowding metric into the Stage 3 gate ✅

- Promote writes a normalized `retail_attention_z` into candidate details →
  flows through `v_gate_input` → one entry added to `MASK_DETAIL_KEYS`.
- The LLM sees "attention 2.8σ above this name's normal" with no identity —
  hype quantified as data crosses the mask; hype-as-headlines cannot.
- Covers the gray zone the hard gate can't express (moderate buzz worrying
  only *in combination*, e.g. with earnings in N days). Tier 1 remains the
  primary defense: Tier 2 is advisory, τ-filtered, absent in dry runs.

### Plumbing

- Scheduler: add a daily `reddit` job + include it in promote's chain
  (`pipeline/scheduler/catalog.py`, one Job line + one tuple entry).
- Retention: reddit.db joins the long-retention list (per-name baselines
  need history; same rule protecting the Stage 6 walk-forward window).

Built 2026-07-05 as `gate_crowding` (G3b, after G3) + `extract.load_crowding`.
Design questions resolved:

- **Threshold form**: BOTH legs required — board rank ≤ `crowding_rank_max`
  (10) AND mentions ≥ `crowding_mult` (3.0) × the name's trailing mean over
  `crowding_baseline_days` (30), computed against the `all-stocks` filter
  only. Baselines thinner than `crowding_min_n` (5 snapshots) pass free
  (the gate self-arms after ~a week of daily reddit jobs).
- **Kill vs size-halve**: kill — gates only kill in v1; a scalar variant is
  a Stage 6 trials question.
- **ETF baseline**: no special case — the per-name norm self-normalizes
  SPY-class permanent chatter.
- **Tier 2**: survivors with a usable baseline get `retail_attention_z`
  (population z vs own baseline, 2dp) appended to details;
  `retail_attention_z` joined `MASK_DETAIL_KEYS`. Advisory, τ-filtered,
  absent in dry runs — by construction.
- **Plumbing**: daily `reddit` scheduler job (no `--keep-days` — long
  retention for baselines); promote chains `after=("leads", "reddit")` and
  receives `--reddit-db`. Missing reddit.db = calm = pass free (stderr
  warning only). Old-repo ApeWisdom history is backfilled under its
  original per-sub filters (`wallstreetbets`/`stocks`/`4chan`) — deliberately
  NOT into `all-stocks`, whose 3-sub-scaled counts would bias live baselines
  low and false-kill top-10 names (see DEPLOYMENT_ROADMAP).
