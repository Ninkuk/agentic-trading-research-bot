# Threshold sweeps select from plateaus, never the argmax

Source: `NLBXgSmRBgU` [00:20:31] — an optimized lookback rarely generalizes;
find a region where a wide range of values performs decently, pick a reasonable
value inside it, and stick with it.

## Landing zone

Research-skill / methodology hardening — the calibration-pass procedure run
before promoting or re-tuning any `sources/combiners/composite/catalog.py`
threshold constant. No code change, no new job, no new data; it amends how the
already-mandated "one measured recalibration pass" chooses its number.

## The defect it prevents

Argmax selection over a sweep is exactly the selection-over-noise mechanism the
repo's calibration history has been burned by (three pre-data threshold
misfires). Picking the sweep's best cell inherits the full data-mining bias of
the sweep; picking from a plateau caps it, at zero cost.

## Shape

A rule added to the calibration procedure, not a table:

- Report the **full sweep curve** in the calibration note, never only the
  winner.
- The chosen threshold must sit on a plateau: neighboring grid values retain
  most of its objective. The tolerance ("most" = X% within ±1 grid step) is
  chosen after the first real sweep is on the table, never before.
- A threshold whose objective collapses one grid step away is rejected even if
  it is the argmax.

## Measurement plan

- **Null / horizon / effective n**: inherited from whatever sweep runs — this
  rule adds no estimate of its own, it constrains the selection step. Effective
  n is still counted in distinct composite dates, per the scorer discipline.
- **Threshold**: the plateau tolerance itself is a post-data choice, recorded in
  the calibration note alongside the curve.
- **Acceptance**: on the first real sweep, record both the argmax and the
  plateau pick; the scorer's ordinary grading of the shipped threshold is the
  long-run scoreboard. No sweep can validly run today (9 distinct matured
  composite dates) — the rule waits with the sweep, costing nothing meanwhile.
