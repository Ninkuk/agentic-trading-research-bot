# Scorer permanent price ledger — design

**Date:** 2026-07-06
**Status:** approved (roadmap item 3; done-when fixed in the roadmap entry)

## Problem

`prune` deletes `prices` rows older than `PRICE_KEEP_DAYS = 90` — the only
growing price series in the system, discarded on a rolling basis. Every
pruned day is backtest evidence permanently lost, and the retention buys
almost nothing: daily closes for ~11k symbols cost on the order of a few
hundred MB per year.

## Design

- Drop the `DELETE FROM prices` from `prune` and the `PRICE_KEEP_DAYS`
  constant; `prune` keeps only its run-header cleanup. The ledger becomes
  append-only and permanent, like the outcome tables.
- Docstrings updated (module header "rolling ledger" → permanent;
  `prune`).
- `docs/SCHEDULE.md` scorer row notes the expected disk growth.
- Test `test_prune_never_touches_outcomes` flips its price assertion:
  ancient ledger rows now survive; run headers still prune.

Stale-junk rows (e.g. the recycled-ticker VII 2018 close) persist forever —
harmless: the forward entry guard, gap guard, and basis guard all refuse to
grade across them, and `v_basis_breaks` keeps them visible.

## Out of scope

An OHLC bar store and vintage-aware backfill (roadmap item 7).
