# Shared-risk factor audit (salvaged)

**Implemented** — research-ticker Phase 3 (factor + overlap step) and
thesis-template §1 (the factor line). TDD record: baseline 0/4 surfaced
overlap; edited spec 4/4 line-compliant; scenario-match wording verified 3/3.

Source: Drew Cohen, "How to Increase Your Chances of Investing Success"
(SXky7-jHYBg, 2026-08-22), [00:19:31]–[00:22:30]. Parent concept — measure
diversification by latent shared risk factors, not industry classification —
died at gate 5: no admissible feed carries per-company factor exposure, and the
industry fields the repo does hold are exactly the grain the concept rejects.

SALVAGED: pipeline-level factor model → research-skill hardening: each buy-side
thesis names its dominant shared risk factor and checks it against the factors
already named by current holdings' theses.

## Landing zone

Research-skill hardening: `research-ticker` (thesis format) and `kill-thesis`
(one attack). No source, no combiner, no schedule slot.

## Shape

- Thesis format gains one required field: **Dominant shared risk factor** — the
  single exogenous condition under which this position and others fail together
  (e.g. "AI capex pace", "China supply chain", "SMB software spend"), stated at
  factor grain, never as a sector label.
- On a buy verdict, the skill lists current holdings (`portfolio.db`
  `v_latest_*`, read-only), reads the factor line from each holding's latest
  `research/<TICKER>-*.md`, and states the overlap count in the thesis.
- `kill-thesis` gains no new gate; the factor line becomes attackable like any
  other enumerated condition.

Coverage today: advisor groups only same-underlying legs (`v_group_heat`) and is
documented look-through-blind; no repo layer sees cross-ticker factor overlap.
Book is 15 equity positions.

## Measurement plan

No pre-set threshold and no scorer wiring — the field is an annotation. After
~20 theses carry factor lines, check whether same-factor holdings co-drew down
(pairwise same-factor vs cross-factor drawdown overlap from the equity ledger);
only then decide whether overlap should ever inform advisor caps. Skill edit
itself goes through the `writing-skills` TDD gate.
