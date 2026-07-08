# Signal-efficacy → reweighting decision-support report — design

Status: design only. No code ships from this document. Every SQL query below
was validated read-only against the live `data/scorer.db` (see the appendix).

## 1. Goal & non-goal

**Goal.** Produce a human-readable ranking of the 23 `composite/catalog.py`
signals by *measured* efficacy (`scorer.v_signal_efficacy`), with each signal
classified into one of: **keep**, **watch**, **insufficient evidence**, or
**drop / consider inverting**. The report is read by a human before they hand-
edit `composite/catalog.py` scoring or weights — it closes the loop from
"the scorer grades outcomes" to "a person acts on the grade," nothing more.

**Non-goal.** Auto-adjusting composite weights, auto-editing `catalog.py`, or
any code path that lets a computed recommendation flow back into how
`composite/db.py:write_ticker_scores` counts votes. Composite's current model
is intentionally simple counting (`SUM(score>0)`, `SUM(score<0)`, `SUM(score)`,
every signal weight 1) — this report never touches that logic. Re-weighting
stays a **human decision**, per the repo's hard invariant (`CLAUDE.md`,
`composite`/`scorer` description) — the executor STOP condition on this plan
is explicit about it, and this design is written to satisfy it: the report's
only output is text/rows for a person to read, never a write path into
`composite.db` or `catalog.py`.

## 2. Ranking model

**Source.** `scorer.v_signal_efficacy`, one row per
`(signal_id, via_crosswalk, horizon)`. Columns used: `signal_id`,
`via_crosswalk`, `horizon`, `n_matured`, `n_bench`, `avg_directional_excess`,
`hit_rate`, `hit_ci_lo`, `hit_ci_hi`, `reliable`, `benchmarks`.

**Primary horizon.** `scorer/catalog.py` defines
`HORIZONS = (5, 10, 21)` trading days. The report picks **horizon = 10**
(two trading weeks) as the primary ranking column — short enough to
accumulate `n_bench` reasonably fast (a prerequisite for `reliable` ever
being true given `RELIABLE_MIN_N = 30`), long enough to smooth single-day
noise out of `dir_excess`. Horizons 5 and 21 are shown as secondary context
columns in the same row (same `signal_id`/`via_crosswalk`), not folded into
one score — a signal can be reliable at 10 days and still-thin at 21.

**Ordering.** Within the primary horizon, `reliable = 1` rows sort first
(rank always privileges evidence over unproven optimism), then by
`avg_directional_excess` descending. `reliable = 0` rows sort after, in their
own "insufficient evidence" block, unordered by excess (ordering unreliable
numbers implies a confidence the sample doesn't support).

**Gating recommendations, not just display.** The keep/watch/drop label is
computed **only** from `reliable`-gated rows. A `reliable = 0` signal_id
*never* receives a keep/watch/drop verdict — see the small-n policy below.
This is deliberate belt-and-suspenders: `reliable` already gates on
`n_bench >= RELIABLE_MIN_N` (30) inside the view, but the report re-checks it
rather than trusting a boolean it didn't compute, in case a future view edit
loosens the gate without a matching plan review.

**Small-n policy.** Any `(signal_id, via_crosswalk, horizon)` with
`n_bench < RELIABLE_MIN_N` (30) — i.e. `reliable = 0` — is labeled exactly:

> **"insufficient evidence — no recommendation"**

No excess/hit-rate number is surfaced as if it were a verdict; the raw
`n_bench`, `n_matured`, and (if present) point-estimate `avg_directional_excess`
/ `hit_rate` may still be shown for transparency, but always next to the
"insufficient evidence" label, never instead of it. Given the plan's own
observation that `v_signal_efficacy` is currently empty (young scorer), the
report must render a clean "insufficient evidence" table for **all 23
signals** on day one and degrade gracefully as `n_bench` climbs — that's the
expected steady state for weeks, not an error path.

**`via_crosswalk` split.** `via_crosswalk = 0` (direct ticker/market/regime
evidence) and `via_crosswalk = 1` (asset-class signal fanned out to its
crosswalk tickers, e.g. `cftc_mm_extreme` graded through `XLE`/`XOM`/...) are
**never merged into one row**. They are shown as two separate ranked
sub-tables under the same `signal_id` heading, each with its own `n_bench`,
CI, and label. Rationale: crosswalk evidence is a proxy bet (the asset class
moved, not necessarily the individual crosswalk ticker), and mixing it with
direct evidence would understate uncertainty and misattribute a proxy's
noise to the signal itself — the same reasoning `db.py`'s comment at
`scorer/db.py:240-245` already encodes ("Crosswalked evidence is split out so
mapped scores are graded separately").

## 3. Anti-signal detection

**Predicate (hit-rate CI based, the recommended one):**

```sql
reliable = 1 AND hit_ci_hi < 0.5
```

A signal earns this only when it is *statistically* worse than a coin flip —
its entire 95% Wilson CI on hit-rate sits below 0.5 — **and** it already
cleared the `n_bench >= 30` reliability floor. This is the only anti-signal
rule the report computes, because `hit_ci_lo`/`hit_ci_hi` are the one column
pair in the view that actually carries an uncertainty bound; the excess-based
formulation ("CI entirely below zero directional excess") sketched in the
plan is **not implementable as-is** — `avg_directional_excess` has no CI
column in `v_signal_efficacy` (only `hit_rate` does; excess is a plain
`AVG()`). Building an excess-based interval would need bootstrapping or a
t-interval over `dir_excess`, which is out of scope for a report that must
stay stdlib-SQL — noted as a **future extension**, not built here.

**Consider-inverting vs. drop.** The report does not try to auto-distinguish
these — both land in one "anti-signal (reliable, CI below 0.5)" bucket with
the raw numbers shown; a human decides whether the fix is removing the
signal from `catalog.py`'s `SIGNALS` list or flipping its score sign (e.g. if
`hit_ci_hi < 0.5` at a magnitude suggesting the *sign convention itself* is
backwards rather than the phenomenon being noise). That interpretive call —
"drop" vs "invert" — is exactly the human judgment this report defers to.

Validated (Step 3, appendix Query C): the predicate runs cleanly against the
live view and currently returns `[]` (no signal has any `reliable=1` rows
yet — expected, see Non-goal/small-n discussion above).

## 4. Output shape

**Recommendation: a new read-only view in `scorer.db`, not a `main.py`
report and not new dashboard code.**

Rationale:
- `scorer.db` already owns the efficacy measurement (`v_signal_efficacy`,
  `v_bucket_performance`) — adding one more `v_*` view there (e.g.
  `v_signal_recommendation`) keeps the "ELT, not ETL" convention: derive the
  label in SQL, don't compute it in a Python report script that could drift
  from the view's own numbers.
- It composes for free with **plan 002** (zero-dep HTML dashboard) — that
  plan's renderer can `SELECT * FROM v_signal_recommendation` exactly like it
  would any other `v_*` view, with zero new plumbing.
- It stays queryable ad hoc (`sqlite3 data/scorer.db "SELECT ... FROM
  v_signal_recommendation"`) without invoking a report generator at all —
  matching how the rest of the repo already treats views as the interface.
- A `main.py`-dispatched text/JSON report was considered and rejected as the
  *primary* surface (though nothing stops a thin `main.py` subcommand later
  that just formats this view for a terminal) — a full dispatcher entry adds
  a `run.py`/`fetch.py` shape this doesn't need (no network, no snapshot
  writer) and would duplicate logic the view already expresses declaratively.

**Sketch — `v_signal_recommendation` columns** (built on top of
`v_signal_efficacy`, GROUP BY nothing extra, one row per existing
`(signal_id, via_crosswalk, horizon)`):

| column | source | notes |
|---|---|---|
| `signal_id` | passthrough | |
| `via_crosswalk` | passthrough | |
| `horizon` | passthrough | |
| `n_bench` | passthrough | the evidence count a human should look at first |
| `avg_directional_excess` | passthrough | |
| `hit_rate`, `hit_ci_lo`, `hit_ci_hi` | passthrough | |
| `reliable` | passthrough | |
| `recommendation` | derived | `'insufficient evidence'` when `reliable=0`; else `'anti-signal'` when `hit_ci_hi < 0.5`; else `'keep'` when `hit_ci_lo > 0.5`; else `'watch'` (reliable but CI straddles 0.5 — directionally unproven either way) |

`'watch'` is the CI-straddles-0.5 case: enough evidence to trust the number
exists, but not enough separation from chance to call it good or bad — a
distinct state from `'insufficient evidence'` (not enough evidence to trust
*any* number) and deliberately not merged with either 'keep' or 'anti-signal'.

## 5. Cadence & placement

The report is only meaningful **after** the nightly `scorer` run (9:10pm
Phoenix, per `docs/SCHEDULE.md`), since that's what advances `n_bench` and
matures outcome rows. Two options:

- **Nightly** (piggyback on `scorer`'s 9:10pm slot or `daily-summary`'s
  9:15pm slot): cheapest to wire, but the underlying numbers move slowly —
  `n_bench` grows by at most a handful of matured rows per signal per night,
  so a nightly re-render mostly repeats itself. Also risks the same crash-
  isolation trap `daily-summary` already learned from (a NULL-heavy helper
  killing the whole digest) if bolted on carelessly.
- **Weekly (recommended)**: a new launchd slot (like the existing weekly
  `backtest` Sat 7:30am or `fred-vintages`) run once a human is actually
  going to *read* it and consider editing `catalog.py` — matching the human's
  reweighting ritual explicitly called out in the plan's "Why this matters."
  `scorer` already runs nightly regardless, so no new dependency is needed:
  the weekly report job just queries `scorer.db` read-only, same pattern as
  `backtest` reading `fred.db` read-only.

This design defers picking the exact slot/day to the eventual build plan
(maintenance note in plan 001) — recommending **weekly**, off the nightly
critical path, is the call this section makes.

## 6. Guardrails against misuse

1. **Lead with `n_bench` and the CI, never with the excess number alone.**
   Every row in the recommended output shows `n_bench` and
   `[hit_ci_lo, hit_ci_hi]` before or alongside `avg_directional_excess`, so
   a human skimming the report sees the sample size and uncertainty in the
   same glance as the point estimate — never just a bare "+2.3% excess"
   that looks more confident than it is.
2. **Never rank an unreliable signal above a reliable one.** The ordering
   rule in §2 hard-codes `reliable DESC` before `avg_directional_excess DESC`
   — a `reliable=0` signal with a flashy 8% excess on `n_bench=4` cannot
   out-rank a `reliable=1` signal with a modest 1% excess on `n_bench=90`.
   This is the direct fix for the "n=12-looks-brilliant failure" the Wilson
   CI comment in `scorer/db.py:27-33` already warns about.
3. **Label state explicitly, in words, not just color/sort order.** Every
   row carries one of exactly four recommendation strings (`'insufficient
   evidence'`, `'anti-signal'`, `'watch'`, `'keep'`) rather than a numeric
   score a reader might over-interpret as precise — and the multiple-
   comparisons caveat from `scorer/db.py:27-33` ("~144 simultaneous rows...
   ~7 look significant at 95% by chance alone") belongs in the report's
   header text verbatim, so a human reading a `'keep'` row still holds it
   loosely rather than treating one week's crossing of the CI threshold as
   proof.

## 7. Validated SQL appendix

All queries run via:
`uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute(<SQL>).fetchall())"`
against the live, read-only `data/scorer.db` from the executor worktree.
Every query below exited 0. All returned `[]` (empty) — expected: the scorer
is young and `v_signal_efficacy` has zero matured, benchmarked rows as of
this plan's commit (`ef40b0c`). `[]` is a pass per the plan's stated
acceptance criterion, not a failure.

**Query A — full efficacy dump (Step 1, the plan's own validation command):**

```sql
SELECT signal_id, via_crosswalk, horizon, n_matured, n_bench,
       avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable
FROM v_signal_efficacy
ORDER BY horizon, signal_id
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, via_crosswalk, horizon, n_matured, n_bench, avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable FROM v_signal_efficacy ORDER BY horizon, signal_id LIMIT 40').fetchall())"
```
Result: `[]`. Exit 0.

**Query B — ranked signals at the primary horizon (§2), direct evidence only:**

```sql
SELECT signal_id, n_bench, avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable
FROM v_signal_efficacy
WHERE via_crosswalk = 0 AND horizon = 10
ORDER BY reliable DESC, avg_directional_excess DESC
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, n_bench, avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable FROM v_signal_efficacy WHERE via_crosswalk = 0 AND horizon = 10 ORDER BY reliable DESC, avg_directional_excess DESC').fetchall())"
```
Result: `[]`. Exit 0.

**Query C — anti-signal predicate (§3):**

```sql
SELECT signal_id, via_crosswalk, horizon, n_bench, hit_rate, hit_ci_lo, hit_ci_hi, avg_directional_excess
FROM v_signal_efficacy
WHERE reliable = 1 AND hit_ci_hi < 0.5
ORDER BY horizon, signal_id
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, via_crosswalk, horizon, n_bench, hit_rate, hit_ci_lo, hit_ci_hi, avg_directional_excess FROM v_signal_efficacy WHERE reliable = 1 AND hit_ci_hi < 0.5 ORDER BY horizon, signal_id').fetchall())"
```
Result: `[]`. Exit 0.

**Query D — insufficient-evidence set (§2 small-n policy):**

```sql
SELECT signal_id, via_crosswalk, horizon, n_bench, n_matured
FROM v_signal_efficacy
WHERE n_bench < 30
ORDER BY horizon, signal_id
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, via_crosswalk, horizon, n_bench, n_matured FROM v_signal_efficacy WHERE n_bench < 30 ORDER BY horizon, signal_id').fetchall())"
```
Result: `[]`. Exit 0. (Note: on live data this will actually be the *populated*
table for a long while — every signal starts here. Empty right now only
because `v_signal_efficacy` itself has zero rows; once outcomes mature this
query becomes non-empty long before Query B/C do.)

**Query E — crosswalk evidence shown separately (§2):**

```sql
SELECT signal_id, horizon, n_bench, avg_directional_excess, hit_rate, reliable, benchmarks
FROM v_signal_efficacy
WHERE via_crosswalk = 1
ORDER BY horizon, signal_id
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT signal_id, horizon, n_bench, avg_directional_excess, hit_rate, reliable, benchmarks FROM v_signal_efficacy WHERE via_crosswalk = 1 ORDER BY horizon, signal_id').fetchall())"
```
Result: `[]`. Exit 0.

**Query F — bucket-level sanity cross-check (§ "Current state" cite of
`v_bucket_performance` as the aggregate-scorecard counterpart):**

```sql
SELECT bucket, horizon, n_matured, avg_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable
FROM v_bucket_performance
ORDER BY horizon, bucket
```

Command:
```
uv run python -c "import sqlite3; c=sqlite3.connect('file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro',uri=True); print(c.execute('SELECT bucket, horizon, n_matured, avg_excess, hit_rate, hit_ci_lo, hit_ci_hi, reliable FROM v_bucket_performance ORDER BY horizon, bucket').fetchall())"
```
Result: `[]`. Exit 0.

## Maintenance notes (carried from plan 001)

- The eventual build plan decides exactly where `v_signal_recommendation`
  lives (this design recommends `scorer/db.py`, alongside
  `v_signal_efficacy`) and whether a `main.py` formatter subcommand is worth
  adding on top of the view.
- New signals added to `composite/catalog.py` appear in
  `v_signal_efficacy` — and therefore in `v_signal_recommendation` — once
  graded; no catalog change is needed on the report side.
- Deferred: implementation of `v_signal_recommendation`, any weekly launchd
  slot, wiring into `deploy/launchd/daily_summary.py` or the plan-002
  dashboard, and the excess-based (bootstrapped) anti-signal CI noted in §3
  as a future extension.
