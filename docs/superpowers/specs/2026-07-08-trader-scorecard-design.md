# Design: Periodic Trader Decision-Quality Scorecard

- **Status**: design spec (not implemented)
- **Planned at**: commit `ef40b0c`, 2026-07-08
- **Source plan**: `plans/004-trader-scorecard.md` (see repo plan index)
- **Depends on**: nothing to implement this; becomes a monthly section of the
  plan-002 dashboard once both exist

## 1. Goal & non-goal

**Goal**: a monthly, read-only report that grades the human's discretion —
whether acting on flagged opinions beats passing on them, what execution
(slippage, fill lag) costs, whether acted trades agree with the opinion the
human actually saw, and how "freelance" trades (no matched opinion) perform
against the recommended book. The genuinely differentiated data this system
already collects is a grade on the *operator*, not just the model; today that
grade is computed by four SQL views in `sources/combiners/scorer/db.py` but
surfaces nowhere except ad hoc queries. This design turns that into a
readable recurring report.

**Non-goals** (explicit):
- No auto-adjusting behavior. The scorecard never re-weights the composite
  catalog, changes advisor sizing, or feeds back into any screener/combiner.
  Re-weighting stays a human decision, exactly as `v_signal_efficacy` /
  `v_bucket_performance` already are for the model side (see CLAUDE.md,
  scorer section).
- No order generation. This is decision support/reflection only.
- No change to the journal schema or the `journal` dispatcher
  (`sources/combiners/scorer/journal.py`). Every view this design reads
  already exists and is unmodified by this plan.
- No new database. The scorecard reads `data/scorer.db` only, read-only.

## 2. Current state (what already exists)

Four views in `sources/combiners/scorer/db.py` carry the raw material:

| View | Line | What it answers |
|---|---|---|
| `v_flag_response` | `db.py:368` | Per matured flagged opinion (`ABS(score_sum) >= FLAG_MIN_ABS_SCORE=4` and `total >= FLAG_MIN_TOTAL=3`, `db.py:40-41`), what the human did: `response` ∈ `{acted, passed, passed_inferred}`, plus `dir_excess` (excess return in the flag's direction) |
| `v_human_filter` | `db.py:391` | `v_flag_response` grouped by `(response, horizon)`: `n`, `avg_dir_excess`, `avg_fwd_return` — the headline "does acting beat passing" table |
| `v_decision_outcomes` | `db.py:324` | Per acted decision, joined to its graded outcome row: `aligned` (0/1/NULL — did the trade agree with the opinion seen), `entry_slippage` (signed; positive is always a cost), `fill_lag_days`, `realized_return` (fills-only), one row **per horizon** the decision matured against |
| `v_freelance` | `db.py:402` | Acted decisions with no matched opinion (`composite_snapshot_id IS NULL`): `realized_return`, `placed_agent`, `source`. Automatic drip/recurring fills are included by design — filter `placed_agent NOT IN ('drip','recurring')` (see `journal.py:35`, `AUTOMATIC_AGENTS`) to see deliberate freelance trades only |

Today's only consumer is `deploy/launchd/daily_summary.py`, and it renders
none of these — the nightly digest shows composite run counts, scorer run
counts, and advisor book heat, but nothing from the decision journal. This
data is effectively unread today.

**Horizons**: `sources.combiners.scorer.catalog.HORIZONS = (5, 10, 21)`
trading days. Every decision that matures gets one `v_decision_outcomes` row
per horizon it's graded against — this is the "one row per horizon" hazard
called out in `db.py:315-316` and re-verified in section 4 below.

**Live-data check (2026-07-08, against `data/scorer.db`, read-only)**: the
journal currently holds exactly 2 acted decisions, both still ungraded
(`horizon IS NULL` in `v_decision_outcomes` — the ticker hasn't matured yet),
and both appear in `v_freelance` (one deliberate, `XOM/buy`, `placed_agent
NULL`; one automatic drip, `DHR/buy`). `v_human_filter` and `v_flag_response`
are both empty — no flagged opinion has matured with a matched or inferred
response yet. This is the small-n reality the plan calls out: the report
must be built to say "insufficient data" cleanly, not to fail or fabricate
signal from 0-2 rows. See §6 for the exact commands and output.

## 3. Metrics catalog

Each section below states the query, what it tells the trader, and the
small-n caveat specific to that section.

### 3.1 Filter edge — "does acting beat passing?"

```sql
SELECT response, horizon, n, avg_dir_excess, avg_fwd_return
FROM v_human_filter
ORDER BY horizon, response;
```

Read per horizon: compare `avg_dir_excess` for `response = 'acted'` vs
`response IN ('passed', 'passed_inferred')`. A positive gap where `acted` n
is sufficient means discretion is adding value on this horizon; a negative
gap means the operator is a net drag on flagged opinions and would have done
better rubber-stamping the model. `passed_inferred` decisions never
explicitly logged a pass (see `db.py:375-382`'s `COALESCE(..., 'passed_inferred')`
fallback) — report it as its own row, don't merge into `passed`, since it is
a weaker inference (absence of an aligned trade, not a recorded decision).

**This is the headline section.** Lead the report with it, and always show
`n` beside every average — the view's own doc comment says "plain averages +
n day one; the Wilson helpers can grade this once samples justify it"
(`db.py:388-389`). This report follows that same discipline: no confidence
intervals until n justifies them.

### 3.2 Execution cost

```sql
SELECT horizon, COUNT(*) AS n,
       AVG(entry_slippage) AS avg_entry_slippage,
       AVG(fill_lag_days) AS avg_fill_lag_days
FROM v_decision_outcomes
WHERE horizon = :h              -- one horizon at a time, see §4
GROUP BY horizon;
```

`entry_slippage` is signed so that positive always means cost (paid above
paper entry on a buy, received below it on a sell) — report it as "cost in
% of entry price," not as a raw signed number a reader might misinterpret.
`fill_lag_days` (`julianday(fill_date) - julianday(entry_date)`) explains
slippage that is really drift from a late fill rather than bad execution —
show both side by side so a large slippage number with a large lag reads
differently than the same slippage with same-day fill.

### 3.3 Alignment

```sql
SELECT horizon, aligned, COUNT(*) AS n
FROM v_decision_outcomes
WHERE horizon = :h              -- one horizon at a time, see §4
GROUP BY horizon, aligned;
```

Report the share where `aligned = 1` vs `aligned = 0` vs `aligned IS NULL`
(NULL happens when `d.opinion_score_sum IS NULL` — the decision matched a
window with no registered opinion yet). `aligned` judges the decision
against the opinion the human **actually saw** at ingest
(`d.opinion_score_sum`), not the (possibly different) score a weekend rerun
settles on later (`owner_score_sum`, also exposed in the view) — both
columns are in `v_decision_outcomes` if a future iteration wants to show
"would this still look aligned against the graded owner row."

### 3.4 Freelance performance

```sql
SELECT decision_id, symbol, side, realized_return, placed_agent, source
FROM v_freelance
WHERE placed_agent IS NULL OR placed_agent NOT IN ('drip', 'recurring');
```

These are acted trades with **no matched opinion at all** — outside
whatever the model recommended. Report count and `AVG(realized_return)`
(fills-only, so unrealized freelance positions show NULL and are excluded
from the average but should still be counted and listed by name) alongside
the recommended book's realized performance for the same period as an
implicit benchmark. Do not compute a joint aggregate against
`v_decision_outcomes` — freelance and journal-matched trades are disjoint by
construction (`composite_snapshot_id IS NULL` vs not), so keep them as two
separate lines, never blended into one "all trades" number.

## 4. The one-row-per-horizon rule (verified)

`v_decision_outcomes` has **one row per (decision, horizon) pair** once a
decision has matured against `HORIZONS = (5, 10, 21)` — up to 3 rows per
decision. `db.py:315-316`'s comment is explicit: *"filter or group by
horizon before aggregating, or every decision counts len(HORIZONS) times."*

Every query in §3.2 and §3.3 above filters `WHERE horizon = :h` (report one
table per horizon, not a pooled one) or groups by horizon, which satisfies
this. The verification command:

```sql
SELECT COUNT(DISTINCT decision_id) FROM v_decision_outcomes;   -- decisions
SELECT COUNT(*)                    FROM v_decision_outcomes;   -- decision×horizon rows
```

On live data both currently return **2** — the two acted decisions are still
ungraded (`horizon IS NULL`, no `ticker_outcomes` match yet), so the
multiplication hazard doesn't show up yet with real numbers. It will as soon
as a decision matures against more than one horizon; the report must never
run an aggregate over `v_decision_outcomes` without a `GROUP BY horizon` or
an explicit `WHERE horizon = :h`, full stop — this is the single most likely
correctness bug in any implementation, per the plan's maintenance note.

## 5. Small-n policy

- Every headline number is shown with its `n` immediately adjacent — never a
  bare average.
- **Suppression threshold**: for any `(response, horizon)` or
  `(aligned, horizon)` cell with `n < 5`, the report shows "insufficient
  data (n=`<k>`)" instead of the average. 5 is a floor, not a statistical
  guarantee — it exists to stop a single trade's outcome from being read as
  a trend, matching the view's own "plain averages + n day one" stance
  rather than manufacturing false confidence with a formal test.
- A month with zero matured flags or zero acted decisions (the current live
  state) renders the whole filter-edge / alignment sections as "no matured
  data this period" — this is a correct, expected output in an early month,
  not a bug to paper over with N/A-hiding.
- No section is dropped for having zero rows; each always renders its
  header and an explicit "insufficient data" body, so a thin month is
  visibly thin rather than silently missing.

## 6. Cadence & placement

- **Cadence**: monthly. Decisions accrue slowly (the live check found 2
  total, ever) — a monthly cadence matches how slowly the underlying data
  changes and matches a human review rhythm better than nightly noise.
- **Ordering**: run after the nightly scorer has graded the latest window
  (so `ticker_outcomes`/`v_decision_outcomes` reflect the most recent
  maturations), on the first scheduled run of a new calendar month.
- **Data source**: reads `data/scorer.db` only, strictly read-only —
  it computes nothing new in SQL beyond what §3's queries already show; no
  new table, no new writer.
- Not wired into `deploy/launchd/install.py` by this plan — cadence wiring
  is a build-plan concern (see `docs/SCHEDULE.md` for the launchd source of
  truth once an implementation plan exists).

## 7. Output shape (recommendation, not implementation)

Three surfaces were considered:

1. **New read-only `v_*` view(s) in scorer.db** — cleanest with existing
   conventions (ELT: compute in SQL, per CLAUDE.md), but a scorecard is
   fundamentally a *presentation* concern (suppression thresholds, per-
   horizon table layout, "insufficient data" text) that doesn't belong in a
   SQL view — views should stay mechanical, as the existing four are.
2. **New `main.py`-dispatched text/JSON report** — a thin `sources/combiners/
   scorer/scorecard.py` (or a small new module) that runs the §3 queries
   with the horizon/suppression logic in Python and prints a text report
   (mirroring how `daily_summary.py` already renders sourced-from-SQL
   digests). Recommended: this matches the existing shipped pattern most
   closely and keeps the SQL views mechanical.
3. **Monthly section of the plan-002 dashboard** — natural once the
   dashboard exists, but plan 002 hasn't landed; building the scorecard as
   its own small dispatcher first means it's usable standalone in the
   meantime and gives the dashboard a section to fold in later exactly as
   this plan's maintenance notes anticipate.

**Recommendation**: build as a standalone report (option 2) now; fold into
the plan-002 dashboard as a monthly section once that ships (this is
already noted as the intended endpoint in the plan). Sketch of the text
report's sections and columns (no code, no view — this is illustrative
only):

```
=== Trader Decision-Quality Scorecard — <month> ===

Filter edge (acted vs passed, by horizon)
  horizon | response        | n | avg_dir_excess | avg_fwd_return
  ...(or "insufficient data (n=<k>)" per cell)

Execution cost (acted decisions, by horizon)
  horizon | n | avg_entry_slippage (%) | avg_fill_lag_days

Alignment (acted decisions, by horizon)
  horizon | aligned=1 (n) | aligned=0 (n) | aligned=NULL (n)

Freelance trades (deliberate only, placed_agent filter applied)
  decision_id | symbol | side | realized_return
  n=<k>, avg_realized_return=<x or "insufficient data">
```

## 8. Validated SQL appendix

All queries below were run **read-only** against
`file:/Users/ninkuk/agentic-trading-bot/data/scorer.db?mode=ro` on
2026-07-08 (repo at `ef40b0c`). Every query exited 0 with no exception;
results reflect the current (small-n) live state, which is expected and is
not a defect.

**Step 1 — existence + baseline read**
```sql
SELECT response, horizon, n, avg_dir_excess, avg_fwd_return
FROM v_human_filter ORDER BY horizon, response;
-- => []  (no matured flagged opinions yet)

SELECT COUNT(*) FROM v_freelance;         -- => 2
SELECT COUNT(*) FROM v_decision_outcomes; -- => 2
```

**§3.1 Filter edge** — same query as Step 1; `[]` confirms zero matured
flags today (expected, see §2 live-data check).

**§3.2 Execution cost**
```sql
SELECT horizon, COUNT(*) AS n, AVG(entry_slippage), AVG(fill_lag_days)
FROM v_decision_outcomes WHERE horizon = 5 GROUP BY horizon;
-- => []  (both decisions still have horizon IS NULL — ungraded)

SELECT horizon, COUNT(*) AS n, AVG(entry_slippage), AVG(fill_lag_days)
FROM v_decision_outcomes GROUP BY horizon ORDER BY horizon;
-- => [(None, 2, None, None)]  -- both rows fall in the NULL-horizon group
```

**§3.3 Alignment**
```sql
SELECT aligned, COUNT(*) AS n FROM v_decision_outcomes
WHERE horizon = 5 GROUP BY aligned;
-- => []  (no horizon=5 rows exist yet)
```

**§3.4 Freelance performance**
```sql
SELECT decision_id, symbol, side, realized_return, placed_agent, source
FROM v_freelance;
-- => [(1, 'XOM', 'buy', None, None, 'mcp'),
--     (2, 'DHR', 'buy', None, 'drip', 'mcp')]

SELECT decision_id, symbol, side, realized_return, placed_agent, source
FROM v_freelance
WHERE placed_agent IS NULL OR placed_agent NOT IN ('drip', 'recurring');
-- => [(1, 'XOM', 'buy', None, None, 'mcp')]   -- drip DHR correctly excluded

SELECT COUNT(*), AVG(realized_return) FROM v_freelance
WHERE placed_agent IS NULL OR placed_agent NOT IN ('drip', 'recurring');
-- => [(1, None)]  -- 1 deliberate freelance trade, unrealized (no exit fill yet)
```

**§4 One-row-per-horizon verification**
```sql
SELECT COUNT(DISTINCT decision_id) FROM v_decision_outcomes;  -- => 2
SELECT COUNT(*) FROM v_decision_outcomes;                     -- => 2
-- Equal today only because both decisions are still ungraded (horizon
-- IS NULL, one row each). Once either decision matures against multiple
-- HORIZONS entries, COUNT(*) will exceed COUNT(DISTINCT decision_id) and
-- any un-grouped aggregate would double/triple count — hence every §3.2/
-- §3.3 query above groups or filters by horizon.
```

**Drift check**
```
git diff --stat ef40b0c..HEAD -- sources/combiners/scorer/db.py
```
→ empty at design time; the four views (`v_human_filter`, `v_flag_response`,
`v_decision_outcomes`, `v_freelance`) match the excerpts quoted in this
document verbatim, confirmed by direct read of `sources/combiners/scorer/
db.py` lines 308-409.
