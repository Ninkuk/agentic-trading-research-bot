# Design Memory — dashboard

Formalized 2026-08-06 as PRODUCT.md (strategy) + DESIGN.md (visual spec,
named rules) for the impeccable skill; keep all three in sync.

## Brand tone
- Beginner-friendly, practical, calm. Plain-English explanations are a
  feature: every section keeps its note, every stat its caption.
- Avoid: newspaper ornament (serif/brass/margin gutters) — retired 2026-07-30
  after "too stylized, hard to read" feedback.

## System
- shadcn/ui zinc via Tailwind v4 CSS tokens; system-default color scheme with
  manual toggle (`useTheme`, `.dark` on `<html>`).
- Density: comfortable. Radius 0.625rem. Borders over shadows.
- Tones: on/off/mid → emerald/red/amber, soft-tinted badges
  (`Badge variant="up|down|hold"`); text is always the primary channel.

## Layout
- Page width is the `--page-width` token in `:root` (72rem since 2026-08-03,
  was 56rem — tables were clipping). `.page` and StaleBanner both read it;
  StaleBanner renders outside `.page`, so a literal there silently desyncs.
- Prose caps at `max-w-[75ch]` (section notes) — the card is page-wide, which
  is far too wide a measure for the plain-English explanations.
- Section notes are ONE sentence of meaning ("what is this and should I
  care"), never widget anatomy; the long-form explainer lives in the
  per-section About modal (info icon in the header action slot, AboutDialog,
  `sec.about` heading+body blocks from data.py). Anatomy — bar geometry, dot
  colors, column mechanics — goes in an about block, not the note
  (2026-08-03, after "wall of text" feedback).
- One summary card (hero + regime chip + macro KPIs w/ sparklines) above five
  strand Tabs; sections are Cards with note as description, verdict badge in
  the header action slot, caveat as italic bordered footnote.

## Tables & charts
- Tables: sortable headers with persistence, filter box at ≥4 rows, numeric
  right-aligned mono tabular-nums. Merge CI into the hit-rate cell, stacked
  (never a wide inline suffix — it smushes neighbors).
- Expansion ("Show all N") is a two-way toggle and session-only; persisting
  it made every later visit open as a 44,000px wall (2026-08-06).
- Columns whose every value is identical auto-hide at ≥4 rows (DataTable);
  the identity column is exempt.
- Machine ids never render raw: formatCell/StatTile humanize snake_case and
  kebab slugs ("SI days to cover"), raw id kept in a title attribute.
- Glossary popovers portal to document.body (table overflow clips them
  otherwise) and columns fall back to a normalized label→glossary match
  when the exporter sets no term.
- No functional text below 12px or below full muted-foreground contrast
  (the 12px Floor Rule; 10px dir-hints failed AA in light mode).
- No resting shadows (cards, tabs); shadows only on floating layers
  (dialog shadow-lg, tooltips).
- Charts: shadcn ChartContainer/ChartTooltip. Sparklines need hidden
  auto-domain YAxis (zero-baseline turns them into filled boxes) and
  tooltips positioned above the chart. No tiny 2-point sparklines — if the
  series is short, drop the chart.
- Equity curve's SPY series is deliberately neutral gray (`--muted-foreground`,
  dashed): a subordinate benchmark, so it fails the dataviz chroma floor by
  design. Gated checks (CVD separation, normal-vision floor) pass in both modes
  (validated 2026-08-07) — don't "fix" the gray or re-litigate without re-running
  the validator.
- No counts in tab labels (user preference, 2026-07-30).

## Repo conventions
- `src/components/ui/` = shadcn primitives; `src/ui/` = app components.
- `text_lines` reports parse via TextReport with `<pre>` fallback.
- `dist/` is gitignored; publish_dashboard.py force-pushes it to the
  gh-pages orphan branch nightly and requires the noindex meta in
  dist/index.html — keep that tag verbatim.

## Coverage (2026-08-25)
- Seven strands: "Sources" sits between Signals and Research and holds the
  raw-feed cards (dark pools, COT, fails, short volume, EDGAR, …); Signals
  stays composite's opinions, Macro is the verdict plus the week's calendar.
- Every `v_*` view in every source DB is either read by a section
  (`tests/test_dashboard_coverage.py` observes reads via SQLite's authorizer),
  consumed by a combiner, or listed in `dashboard_lib/coverage.UNSURFACED`
  with a reason. A new view fails the suite until one of those is true.
- `GenericSection` renders tiles + table + text together, so an
  exporter-only section (no React component) gets KPI tiles with sparklines
  above its rows. Per-row number arrays render as an inline SVG `Sparkline`
  (not recharts — thirty per leaderboard); tile `history` points use KpiSpark.
- Booleans render as `bool--good` / `bool--bad` pills keyed by column
  semantics (a beaten benchmark is good, a stale ATR is bad); unknown keys
  stay plain yes/no.
- `dashboard/make_fixture.py` merges any new section into
  `src/fixtures/data.json` from synthetic DBs (never data/);
  `test_fixture_carries_every_section` fails until it has been run.
