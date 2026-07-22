# 001 — composite reads options.db (Phase 1: annotation only)

Spec: `docs/superpowers/specs/2026-07-21-composite-options-annotation-design.md`

## Tasks

1. **Tests first (RED)** — extend `tests/test_composite_catalog.py` with an
   "options annotation (plan 001)" section mirroring the `earnings_imminent`
   patterns: catalog shape (ticker grain, `options.db`, budget 4, score literal 0),
   not in `REGIME_FIELDS`, one-clock rule (covered by the existing whole-catalog
   test), `select_ids` round-trip, and a fixture-DB extraction test
   (`sources.screeners.cboe_options.db.ensure_schema`) asserting one score-0 row
   per underlying with SPX/VIX excluded. Extend `tests/test_composite_db_write.py`:
   both ids in `INFORMATIONAL_SIGNALS`, plus a behavioral test that the two
   annotation rows do not lift a one-vote ticker over `v_flagged`'s `total >= 2`.
2. **Implement (GREEN)** — two catalog entries in
   `sources/combiners/composite/catalog.py`; add both ids to
   `db.INFORMATIONAL_SIGNALS` in `sources/combiners/composite/db.py`.
3. **Gates** — ruff check, ruff format, mypy, full pytest.
4. **Smoke-run** — composite into a scratch DB against real `data/`, with and
   without the new signals; assert 22 rows per signal and identical `v_flagged`.
5. **Commit** — docs commit (spec + plan), feat commit (code + tests).

## Out of scope (deferred in spec)

Scored options signals (mid-Sept gate), `v_unusual_activity`, market-regime
additions, advisor iv30 sizing.
