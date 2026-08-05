# Design Memory — dashboard

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
- Charts: shadcn ChartContainer/ChartTooltip. Sparklines need hidden
  auto-domain YAxis (zero-baseline turns them into filled boxes) and
  tooltips positioned above the chart. No tiny 2-point sparklines — if the
  series is short, drop the chart.
- No counts in tab labels (user preference, 2026-07-30).

## Repo conventions
- `src/components/ui/` = shadcn primitives; `src/ui/` = app components.
- `text_lines` reports parse via TextReport with `<pre>` fallback.
- `dist/` is gitignored; publish_dashboard.py force-pushes it to the
  gh-pages orphan branch nightly and requires the noindex meta in
  dist/index.html — keep that tag verbatim.
