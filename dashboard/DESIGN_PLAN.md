# Design Implementation Plan: Dashboard Main (shadcn redesign)

Winner: design-lab Variant C ("Tabbed strands"), rounds 1-5 of feedback applied.
Lab preview verified in-browser before finalize; lab artifacts deleted on completion.

## Direction

- shadcn/ui zinc tokens, Tailwind v4 (CSS-first `@theme`), system-default
  light/dark with a manual toggle.
- Layout: combined summary card (hero bullets + regime chip + macro KPIs with
  sparklines) pinned above five strand Tabs; every section renders in its
  strand via shape dispatch. The ledger margin-note gutter is gone — the
  section note becomes the card description under each title.
- Tables: existing DataTable logic (sort persistence, pinning, show-all,
  Term-in-header) restyled on the shadcn table kit + a text filter at ≥4 rows.
  TanStack Table was evaluated in the lab and NOT kept — the tested in-house
  sort covers everything the design needs.
- Charts: shadcn chart kit (ChartContainer + ChartTooltip) over the existing
  Recharts dep. Sparkline tooltips float above the mark (a tooltip larger
  than a 96px chart must escape the viewbox). Hidden YAxis with auto domain —
  without it Recharts baselines areas at 0 and a series near 14 fills solid.
- Trader scorecard: text_lines parsed client-side (`TextReport`) into titled
  subsections + tables, `<pre>` fallback on parse failure. Class fix (later,
  Python side): the exporter should emit structured JSON for plan-004.
- Designed degraded states: empty (dashed box + exporter's own message),
  error (red mono alert), both inside the normal card shell.

## Files

- `src/index.css` — replaced: Tailwind + zinc tokens (+`--tone-*` for
  recharts strokes) + component layer for retained widget classes
  (score bar, meter, CI plot, tiles, term popover).
- `src/components/ui/` — card, badge, button, table, tabs, separator, input,
  chart (sanitized ChartStyle injection).
- `src/hooks/useTheme.ts` — system/light/dark, `.dark` on `<html>`.
- `src/ui/` — Masthead (compact header + search + theme toggle), SectionShell
  (Card shell), DataTable (shadcn styling + filter), VerdictChip/StatTile/
  CaveatLine/Banners restyled; StrandNav deleted (tabs replace it).
- `src/ui/TextReport.tsx`, `src/charts/KpiSpark.tsx` — from lab.
- `src/ui/sectionCells.tsx` — the lab's column-key heuristics as the shared
  cell formatter (tinted scores/excess, stacked hit-rate CI, pills, usd/pct);
  replaces `advisorCell` and the retired widgets. Deleted outright:
  ScoreBar, EfficacyDotPlot, Sparkline, MacroDrivers section (its rendering
  is the summary-card KPI row), StrandNav.
- `src/routes/Main.tsx` — summary card + Tabs (macro-drivers lives in the
  summary card, not its strand; unknown kickers still get an "Other" tab).
- `src/routes/TickerDetail.tsx` — restyled on the same kit.

## Checks

- All vitest suites updated with the structure (tabs mount via forceMount so
  section queries still see the whole document); tsc, oxlint clean.
- `dist/` is gitignored — publishing is deploy/launchd/publish_dashboard.py,
  which force-pushes dist + the real reports/data.json to a single-commit
  gh-pages orphan branch nightly and verifies the noindex guard in
  dist/index.html. Keep `npm run build` fresh after UI changes so the next
  publish run ships them.
