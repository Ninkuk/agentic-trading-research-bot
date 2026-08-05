# Drop 2-point sparklines in KpiSpark per the documented minimum

Written against: 805489c

## Evidence chain

- Surface: `dashboard/src/charts/KpiSpark.tsx`, rendered in the Main route's
  summary card for each macro-drivers tile with history
  (`src/routes/Main.tsx:222`).
- Problem: the guard at `KpiSpark.tsx:29-30` is
  `if (usable.length < 2) return null;` — a series with exactly 2 usable
  (non-null) points renders a 96×36 sparkline.
- Design evidence: `dashboard/DESIGN_MEMORY.md:27-28` — "No tiny 2-point
  sparklines — if the series is short, drop the chart."
- Owner: `KpiSpark` is the only sparkline component on the surface (repo-wide
  grep at 805489c; the scorecard's history renders through other cells).
- Scope and affected surfaces: summary-card macro KPIs only. Latent today —
  live series carry 90 points — but deterministic for any newly added or
  sparse FRED series, and for nulls thinning a series to 2 usable points.
- Uncertainty: none on the contract; the exact minimum above 2 is not
  specified, so the change uses the smallest correction the rule requires.

## Design decision

Raise the guard so an exactly-2-point series drops the chart (the tile still
shows value, delta, and label — only the chart slot goes empty), matching the
recorded decision. Three points remains the minimum that renders.

## Reuse

- Exemplar: the existing guard shape in `KpiSpark.tsx:29-30` and the same
  pattern in `TickerDetail.tsx`'s `ScoreHistoryChart` (`usable.length < 2`
  with a text fallback) — that chart is a full-size 180px chart, not a tiny
  sparkline, and is NOT governed by the sparkline rule; leave it alone.

No new primitive.

## Changes

1. `dashboard/src/charts/KpiSpark.tsx`
   - Change: guard from `usable.length < 2` to `usable.length < 3`, and
     update the file's header comment ("Degrades to nothing under 2 usable
     points") to say under 3.
   - Preserve: null-point filtering, ChartContainer sizing, hidden
     auto-domain YAxis, tooltip floated above the chart
     (`position={{ y: -46 }}`) — all separately mandated by
     `DESIGN_MEMORY.md:25-28`.
   - Verify: rendering with 2 usable points returns null; with 3, renders.
2. `dashboard/src/charts/` — add `KpiSpark.test.tsx` (none exists at
   805489c)
   - Change: two tests — 2 usable points (including the case where nulls
     reduce a longer series to 2) → no chart; 3 usable points → chart
     renders. Follow the jsdom conventions of `RegimeTimeline.test.tsx`.
   - Verify: `cd dashboard && npx vitest run src/charts/KpiSpark.test.tsx`
     passes.

## Scope

- Inherit: the summary-card KPI row (only `KpiSpark` call site).
- Verify: tiles whose series drop the chart still render value/delta/label
  cleanly (the sparkline is a trailing flex sibling; nothing reflows badly).
- Exclude: `ScoreHistoryChart` in `TickerDetail.tsx` (full-size chart with
  its own `< 2` guard and text fallback — not a sparkline);
  `RegimeTimeline` (full-width chart).

## Validation

- Product: dashboard summary card renders exactly as tonight (all live
  series are 90 points — no visual change expected).
- Interface: a fixture tile with `history` of 2 usable points shows value +
  delta with no chart box.
- System: confirm no other component renders a sparkline that would need the
  same guard (`grep -rn "ChartContainer" dashboard/src` — only KpiSpark,
  RegimeTimeline, TickerDetail).
- Repository: `cd dashboard && npx vitest run && npx oxlint src` → all pass.

## Stop conditions

- Stop if a product decision has changed the documented sparkline rule in
  `DESIGN_MEMORY.md`, or if KpiSpark has gained call sites beyond the
  summary card.

## Design documentation

- After acceptance and validation: none — `DESIGN_MEMORY.md:27-28` already
  records the rule this enforces.
