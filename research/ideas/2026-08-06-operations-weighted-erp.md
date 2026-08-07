# operations-weighted-erp

Source: Damodaran, "Country Risk: Determinants, Measures and Implications — The
2026 Edition" (sres2R8etKA, uploaded 2026-07-15), [00:27:31–00:29:32]; paper at
SSRN abstract 7107638.

**Concept.** A company's hurdle ERP should be weighted by where it *operates* —
never by country of incorporation. Weight by revenues for consumer businesses,
by production for resource extraction, by a stated mix for manufacturers.
Applying the uniform US implied ERP to a name with emerging-market operations
understates the hurdle and overstates the cushion `research-ticker` reads.

**Proving number** (fetched 2026-08-06, `datafile/ctryprem.html`): South Africa
carries a 3.90% country risk premium over the mature-market anchor, Brazil
3.24%. A GFI-type name (in the candidates ADR set) graded against the flat US
ERP has its hurdle understated by roughly 300–400 bps — an order of magnitude
above every other input's noise (the US Aa1 default-spread adjustment from the
same video moves the hurdle by `0.23% × (β−1)` ≤ ~11 bps and died at gate 7).

## Landing zone

Research-skill hardening — `research-ticker`'s
`references/damodaran-anchors.md` (Phase 4 hurdle read). No screener, no
catalog signal, no schedule slot. Keeps the anchors file's existing rule:
nothing here feeds `composite`, `candidates`, or `advisor`.

## Shape

A third run-time fetch in the anchors file, plus a weighting rule:

- Fetch `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html`
  (verified 2026-08-06: HTTP 200, 277 KB static HTML, stdlib-parseable —
  columns: country, Moody's rating, default spread, country risk premium,
  total ERP; e.g. Brazil Ba1/2.13%/3.24%, Germany Aaa/0.00%, US Aa1/0.23%).
  Updated twice a year (July and January per the video) — fetch live, cite
  as-of, never quote pinned examples.
- `ERP_company = Σ wᵢ × ERP_countryᵢ`, weights from the filing's own
  geographic segment disclosure (10-K/20-F — primary source, already read in
  earlier phases). Revenues for consumer, production for resources, stated mix
  for manufacturers. Incorporation country is never a weight.
- Materiality floor so US-only names don't grow a pointless calculation: apply
  only when non-US operations exceed a disclosed-segment threshold chosen at
  write-up time from what filings actually disclose — not fixed here.

## Measurement plan

- **Grading path:** `v_research_filter` (scorer.db) — verdicts anchored
  strictly after `verdict_date`, hit = `fwd_return > bench_fwd_return`, so the
  null is 0.5 and there is no look-ahead in a research-time fetch.
- **Comparison:** once matured, split `v_research_filter` rows by whether the
  name had material non-US operations at verdict time; the concept predicts
  fewer false "attractive" verdicts in the non-US split after adoption.
- **Effective n:** verdict grading began 2026-07; n is currently far too thin
  to read (count DISTINCT verdict dates, not rows, before quoting any n).
  This is an input-consistency fix in the same class as the shipped
  `rf + β × ERP` hurdle — adopted for valuation correctness, with the split
  above as the eventual honesty check, not a pre-adoption gate.
- **Thresholds:** the materiality floor and any weighting-mix conventions are
  chosen after seeing real segment disclosures, never before.
