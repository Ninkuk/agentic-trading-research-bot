# Scorer basis-break guard — design

**Date:** 2026-07-06
**Status:** approved (roadmap item 1; verification 2026-07-06 confirmed the bug)

## Problem

`scorer.db → prices` stores each day's close on whatever price basis the
provider used that day. A split (or large reverse split) changes the basis
mid-ledger; the sources carry no adjusted history to correct from
(`stocks.db`/`etfs.db` snapshots are frozen single bars) and `insert_prices`
is INSERT OR IGNORE, so the break is permanent. Maturation then computes
`exit_close / entry_close - 1` across the break and writes a fabricated
return (synthetic 2:1 split → −49.5 %) into the **never-pruned** outcome
tables. The existing julianday guard only catches calendar gaps.

Zero contaminated rows exist as of design date (ledger is one date per
symbol, nothing matured); first maturations land ~5 trading days after
2026-07-02, so this ships before then.

## Design: refuse-to-grade guard (roadmap option b)

Same principle as the gap guard: **a pending row is visible forever, a wrong
row is permanent.** Maturation refuses any row whose grading window contains
a split-shaped day-over-day move; the row stays pending (it will never
mature — quarantine is permanent unless a human intervenes).

### Break definition

For consecutive ledger dates `(prev, cur)` of one symbol, a **basis break**
is `cur.close < prev.close * BASIS_BREAK_LO` or
`cur.close > prev.close * BASIS_BREAK_HI`, with

```python
BASIS_BREAK_LO = 0.55   # catches forward splits >= 2:1 (ratio 0.50, 0.33, ...)
BASIS_BREAK_HI = 1.80   # catches reverse splits >= 1:2 (ratio 2, 5, 10, ...)
```

Multiplication, not division (no zero-divide; a zero `prev.close` flags
conservatively). Constants live in `db.py` beside `PRICE_KEEP_DAYS` —
grading-integrity constants, not experiment knobs, so not `catalog.py`.

### Guard placement

`_MATURE_SYMBOL` gains two `NOT EXISTS` clauses beside the julianday bound,
scanning consecutive-date pairs where the later date is in
`(entry_date, xdate]`:

1. the graded leg (`t.symbol` / `t.entity`) — protects `fwd_return`;
2. the benchmark leg (`:bench`) — protects `bench_fwd_return` (SPY has
   never split, but the clause is cheap and the failure would be systemic).

`_MATURE_REGIME` gains the benchmark clause (its graded leg *is* the
benchmark).

### Audit view

`v_basis_breaks`: every split-shaped consecutive-date pair in the ledger —
`(symbol, prev_date, prev_close, price_date, close, ratio)`. Thresholds are
baked into the view (schema string interpolates the constants), `mature()`
passes the same constants as query params — one definition, two consumers.
This is how a human distinguishes "pending because young" from "pending
because quarantined" (join `v_pending` × `v_basis_breaks` on symbol).

## Trade-offs accepted

- **Censoring:** a genuine one-day move beyond −45 %/+80 % (rare; biotech
  blowups) is quarantined alongside real splits, censoring the extreme tail
  that squeeze signals target. Mitigation: quarantine is not deletion — the
  row stays in `v_pending`, `v_basis_breaks` shows the evidence, and the
  roadmap's option (a) enrichment (cross-check against the provider's
  split-adjusted `ch1w`/`ch1m`) can later clear false positives.
- **Sub-threshold splits:** a 3:2 split (ratio 0.667) passes the guard and
  still fabricates a ~−33 % error. Tightening LO above 0.55 would censor too
  many real moves; 3:2 splits are rare in the signal universe (small-cap /
  ETF proxies). Documented residual, revisit with option (a).
- **Dividends:** out of scope — continuous small basis drift, not a break;
  partially offset by the benchmark in excess terms. Tracked in the
  roadmap's item 8 backlog.

## Tests (extend existing files, offline as always)

- `test_scorer_db_write.py`:
  - synthetic 2:1 split inside the window → row **stays pending** (the
    verified repro, inverted into the guard's contract);
  - large-but-gradual move (−30 % over 5 days, no single-day break) →
    **matures normally** (guard does not censor legitimate volatility);
  - break *after* `xdate` → matures (window-scoped, not ledger-scoped);
  - benchmark-leg break blocks maturation of symbol rows.
- `test_scorer_db_views.py`: `v_basis_breaks` flags the split pair and
  nothing else on a clean ledger.

## Out of scope

Options (a) provider cross-check and (c) ledger rescaling; dividend
adjustment; any change to registration, harvest, prune, or the CLI.
