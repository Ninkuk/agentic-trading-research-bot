# Design Memory — dashboard

Formalized 2026-08-06 as PRODUCT.md (strategy) + DESIGN.md (visual spec,
named rules) for the impeccable skill; keep all three in sync.

## Brand tone
- Beginner-friendly, practical, calm. Plain-English explanations are a
  feature: every section keeps its note, every stat its caption.
- Avoid: newspaper ornament (serif/brass/margin gutters) — retired 2026-07-30
  after "too stylized, hard to read" feedback.

## System
- shadcn/ui tokens via Tailwind v4, Robinhood palette (since 2026-09-01;
  was zinc): untinted neutral grays, true-black dark ground with cards one
  step up, green `#00c805` as primary (black ink on it) and up tone,
  `#ff5000` as down tone. Light-mode tone TEXT is stepped darker
  (`#008800` / `#d34101`) — the brand green is 2.3:1 on white, below AA.
  System-default color scheme with manual toggle (`useTheme`, `.dark` on
  `<html>`).
- Density: comfortable. Radius 0.75rem; buttons, badges and StrandNav pills
  are `rounded-full`. Borders over shadows.
- Tones: on/off/mid → green/red-orange/amber through the `--tone-*` tokens,
  exposed as `text-tone-up` / `bg-tone-hold-bg` utilities — components never
  hardcode a Tailwind hue for a tone. Soft-tinted badges
  (`Badge variant="up|down|hold"`); text is always the primary channel.
- Stat-tile values are sans tabular figures at 1.375rem/500 (Robinhood's hero
  numbers); tables keep mono for column alignment.

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
- Within a strand: full cards in exporter order, then row-only cards of ≤6
  rows two-up (`md:grid-cols-2`), then one "Quiet tonight" card listing
  empty sections (title, empty sentence, About) — ids stay addressable.
- A strand of ≥8 live cards spread over ≥2 publishers (Sources) regroups
  them under publisher headings (`source` from data.py's PUBLISHERS, keyed
  on the DB: SEC, FINRA, Treasury, NY Fed, …). Group anchors are
  `<strand>-<publisher>`; the hash router resolves them after section ids.
- The rail is the table of contents: each strand is a Collapsible of
  its sub-items (publishers for Sources, live section titles elsewhere,
  truncated with the title in a tooltip), the chevron toggling it, and
  `useScrollSpy` marks the one in view with `aria-current="location"`.
  Landing on a strand opens it; the open set is session state, never a
  pref (a persisted set drifts from where the reader is). Below `lg` the sidebar is a sheet
  that closes on navigation, so the one-line StrandNav chip row (same
  items, same scroll-spy) shows there only. Scroll offsets are
  `scroll-mt-16 lg:scroll-mt-4`: the sticky row exists only below `lg`.
- shadcn Sidebar shell (`src/ui/AppShell.tsx`, since 2026-09-01; replaced
  the strand tab strip): Summary + one item per strand, offcanvas-collapsible
  with the trigger in the masthead, open state in prefs, a Sheet under `lg`
  (1024px — a portrait tablet beside the 16rem rail left ~512px for tables).
  Routes: `#/` Summary, `#/<strand>` a strand, `#/ticker/SYM` drill-down; a
  bare `#<section-id>` resolves to its strand and scrolls (StrandNav links
  keep working). Strands stay force-mounted and class-hidden when inactive.
- Summary page = hero bullets + regime chip card, then a strand index
  (name + one-line blurb from `strands.ts`, linking in). The macro-driver
  KPIs are the macro-drivers card in Macro, right after the regime card
  whose call they decide. Sections are Cards with note as description,
  verdict badge in the header action slot, caveat as italic bordered footnote.

## Tables & charts
- Tables run on TanStack Table v9 (feature API: sorting, global filter, column
  visibility as controlled state) under the shadcn table kit; DataTable owns
  pinned-first partitioning and the page slice outside the row model, so a
  pinned row leads page one rather than its sort-position page.
- Tables: sortable headers with persistence, filter box at ≥4 rows, numeric
  right-aligned mono tabular-nums. Hit rate + CI renders as a RangeCell mark
  (dot, whisker, null-rate tick; digits in the title) — never a wide inline
  suffix, it smushes neighbors. Signed excess renders as a DivergingCell bar at
  zero, weight/heat as a BarCell; makeSectionCell(rows) supplies the column max.
- Long tables page at 8 rows (previous/next chevrons, "1–8 of N" count);
  the page is session-only and returns to one on any filter or sort change.
  Never persist it — the old "Show all N" toggle, once persisted, opened
  every later visit as a 44,000px wall (2026-08-06).
- Columns whose every value is identical auto-hide at ≥4 rows (DataTable);
  the identity column is exempt.
- Machine ids never render raw: formatCell/StatTile humanize snake_case and
  kebab slugs ("SI days to cover"), raw id kept in a title attribute.
- Glossary popovers are shadcn Popover (portals to body — table overflow
  clips an in-flow one — with `role="tooltip"`, hover-open beside click);
  columns fall back to a normalized label→glossary match when the
  exporter sets no term.
- Degraded states go through `EmptyNote` (shadcn Empty) and `Alert`;
  theme switch is a single-select ToggleGroup (items are radios); the
  ticker pin is a `Toggle` in a `Tooltip`; table filters are `InputGroup`;
  Summary's strand index and Quiet-tonight rows are `Item`s.
- No functional text below 12px or below full muted-foreground contrast
  (the 12px Floor Rule; 10px dir-hints failed AA in light mode).
- No resting shadows (cards, sidebar rail); shadows only on floating layers
  (dialog shadow-lg, tooltips).
- Charts: shadcn ChartContainer/ChartTooltip. Small multiples need a hidden
  padded-domain YAxis (zero-baseline turns them into filled boxes). No tiny
  2-point sparklines — if the series is short, drop the chart. `--chart-1..5` run green, blue, gold,
  violet, red-orange in that order (adjacent pairs validated: all dataviz
  checks pass in both modes, worst adjacent CVD ΔE 27); dark is the same
  order re-stepped into L 0.48–0.67 for the `#141414` card. Regime dots use
  `--tone-*`, never hexes.
- Equity curve's SPY series is deliberately neutral gray (`--muted-foreground`,
  dashed): a subordinate benchmark, so it fails the dataviz chroma floor by
  design. Gated checks (CVD separation, normal-vision floor) pass in both modes
  (validated 2026-08-07) — don't "fix" the gray or re-litigate without re-running
  the validator.
- No counts in strand nav labels (user preference, 2026-07-30).

## Repo conventions
- `src/components/ui/` = shadcn primitives; `src/ui/` = app components.
- `text_lines` reports parse via TextReport with `<pre>` fallback; no exporter
  ships them today (the trader scorecard became the structured `your-trades`
  and `trading-the-signals` cards).
- `dist/` is gitignored; publish_dashboard.py force-pushes it to the
  gh-pages orphan branch nightly and requires the noindex meta in
  dist/index.html — keep that tag verbatim.

## Coverage (2026-08-25)
- Seven strands, one kind of content each: Macro = the verdict, calendar,
  yield curve; Signals = composite's opinions plus their calibration and
  replay grades; Sources = raw-feed cards; Research = theses plus research
  and candidate grading; Track record = the human's own record; Ops = worklists.
- Every `v_*` view in every source DB is either read by a section
  (`tests/test_dashboard_coverage.py` observes reads via SQLite's authorizer),
  consumed by a combiner, or listed in `dashboard_lib/coverage.UNSURFACED`
  with a reason. A new view fails the suite until one of those is true.
- `GenericSection` renders tiles + table + text together, so an
  exporter-only section (no React component) gets KPI tiles with sparklines
  above its rows. Per-row number arrays render as an inline SVG `Sparkline`
  (not recharts — thirty per leaderboard); tile `history` points use
  TileCharts/DriverChart (below).
- Tiles with history are small multiples, not KPI tiles: `TileCharts` lays
  them out one column each (`md:grid-cols-{n}` up to four, six wrap as 3×2)
  and each gets a measured-width `DriverChart` (~110px tall, first/middle/
  last date ticks, tooltip inside the plot) — 90 daily points in a 96px
  sparkline left half the card empty and the tooltip on the neighbour's
  headline. Macro drivers also ship `thresholds` (narrative.band_edges, the
  cutoffs behind the tile's band word), drawn as dashed reference lines
  labelled with the band above; `driverDomain` draws a cutoff outside the
  data only when within half the 90-day range, nearest per side, so a far
  cutoff never flattens the series into a ribbon.
- Booleans render as `bool--good` / `bool--bad` pills keyed by column
  semantics (a beaten benchmark is good, a stale ATR is bad); unknown keys
  stay plain yes/no.
- `dashboard/make_fixture.py` merges any new section into
  `src/fixtures/data.json` from synthetic DBs (never data/);
  `test_fixture_carries_every_section` fails until it has been run.
