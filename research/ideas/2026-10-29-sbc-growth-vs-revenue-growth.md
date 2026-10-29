# SBC/revenue trend as a candidates quality-ledger annotation

Source: Aswath Damodaran, "The Prospectus is here: My (but not the) Anthropic
IPO Valuation!" (cd1xrO2q9HU, 2026-10-28), [00:09:02]. Concept as stated: SBC
growing slower than revenue is tolerable; SBC growing faster than revenue is a
drain flag. SBC/revenue rises exactly when SBC grows faster than revenue, so
the `sbcByRevenue` trend is the same quantity with no hand-picked threshold.

Why it is not a duplicate: the screen gates realised dilution (`sharesYoY`),
which buybacks mask, and `research-ticker` deducts the SBC *level* from base
FCF. Neither sees SBC/revenue rising across an on-list episode — the same gap
`v_candidate_quality_trend` already fills for fScore and ROIC.

## Landing zone

`candidates` per-sighting quality ledger (scorer.db `candidate_appearances`),
read by `v_candidate_quality_trend`. Annotation only — never a gate until
`v_candidate_efficacy` shows a split.

## Shape

- `candidates.py` `_FIELDS` gains `sbcByRevenue`; `candidate_appearances`
  gains `sbc_by_revenue REAL` (nullable ALTER via `add_missing_columns`; the
  live DB predates it). Coverage: 1,650 of 2,064 names ≥ $2B carry the field.
- `v_candidate_quality_trend` gains `sbc_entry` / `sbc_now` beside the
  fScore/ROIC/accruals pairs.
- Source is stocks.db (stockanalysis — the approved exception); no new job,
  no new fetch.

## Measurement plan

- Null: the screen's own matured entry-episode base rate in
  `v_candidate_efficacy` (excess over SPY), not 0.5.
- Horizon: 21 and 63 trading days, the horizons the screen already grades.
- Effective n: distinct entry episodes with a non-null `sbc_entry`, counted
  from the column's ship date — no backfill exists, stocks.db keeps ~3 weeks.
- Threshold sweep: split episodes by sign and tercile of `sbc_now − sbc_entry`
  only after ≥ 50 matured 63d episodes carry the column; anything earlier is
  one overlapping market episode.
