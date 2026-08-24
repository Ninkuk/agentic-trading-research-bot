// Mirrors deploy/launchd/dashboard_lib/data.py's export_data() — the shape
// of reports/data.json. Every field that a section/exporter can omit is
// optional here; the client must typecheck against a degraded document
// (missing DB, dropped view, zero rows) exactly as the export itself
// degrades (see data.py's SECTION_EXPORTERS try/except).

export type SectionId = string;

export type Tone = "on" | "off" | "mid";

export interface Verdict {
  text: string;
  tone: Tone;
}

export interface Bullet {
  text: string;
  tone: Tone;
}

export type ColumnDirection = "up-good" | "down-good" | null;

export interface Column {
  key: string;
  label: string;
  numeric: boolean;
  direction?: ColumnDirection;
  term?: string | null;
}

// A row's field values (columns), or a tile's own catch-all fields — plain
// JSON leaves, plus a bare number array for the scorecard's per-row
// `history` sparkline (data.py:339's `list[int] | None`, see
// `_SCORECARD_HISTORY_LIMIT` in dashboard_lib/data.py — headline symbols
// only, `None` for every other row).
export type CellValue = string | number | boolean | number[] | null;

// A table row: the shape varies per section (scorecard vs. regime drivers
// vs. track-record views), so it stays a loose keyed bag rather than a
// per-section union — narrow it at the call site when a specific section's
// columns are known.
export type Row = Record<string, CellValue>;

export interface Tile {
  label: string;
  value?: CellValue;
  band?: string | null;
  tone?: Tone | null;
  // macro-drivers tiles only:
  series_id?: string;
  delta?: number | null;
  history?: { date: string; value: number | null }[];
}

// The six strand groups a section's `kicker` sorts it into (Main.tsx's
// STRANDS, data.py's SECTION_EXPORTERS kicker column). Kept as a real union
// — not a bare `string` — so a hand-authored Section (tests, fixtures the
// Loosen<T> guard checks) gets a compile-time nudge toward a real strand
// name. This can't catch a *live* JSON payload disagreeing at runtime
// (JSON always reads back as plain `string`) — that's what the
// "every fixture section's kicker is a known strand" test in
// fixtures/data.test.ts is for, and why Main.tsx's strand grouping still
// runs a defensive membership check and routes anything unrecognized into
// a trailing "Other" group rather than ever silently dropping it.
export type Kicker = "Macro" | "Signals" | "Research" | "Track record" | "Your book" | "Ops";

// Canonical strand order — the single source Main.tsx, StrandNav, and the
// fixture drift test all read from, so the list can't fork. "Ops" is
// appended last: pipeline health is plumbing, not signal.
export const KICKERS: readonly Kicker[] = [
  "Macro",
  "Signals",
  "Research",
  "Track record",
  "Your book",
  "Ops",
];

// One section of the document (sections[<id>]). A section that failed to
// export degrades to `{ title, kicker, note, error }` only — every other
// field is therefore optional. A healthy section carries some subset of
// verdict/tiles/columns/rows/text_lines depending on its exporter (see
// data.py's per-section return shapes: tile sections like `regime`/
// `book-heat`, table sections like `scorecard`/`signal-efficacy`, and the
// text-only `trader-scorecard`).
// One headed block of a section's long-form explainer, shown in the About
// modal (data.py's SECTION_EXPORTERS `about` column).
export interface AboutBlock {
  heading: string;
  body: string;
}

export interface Section {
  title?: string;
  kicker?: Kicker;
  note?: string;
  about?: AboutBlock[];
  verdict?: Verdict | null;
  tiles?: Tile[];
  columns?: Column[];
  rows?: Row[];
  text_lines?: string[];
  caveat?: string | null;
  empty?: string;
  total?: number;
  error?: string;
  // candidates-only:
  snapshot_date?: string | null;
  // equity-curve-only:
  curve?: EquityCurvePoint[];
  curve_summary?: EquityCurveSummary;
  // research-reopens-only:
  dated?: number;
  events?: number;
  checkpoints?: ReopenCheckpoint[];
  // health-only:
  healthy?: boolean;
}

// equity-curve-only: one charted date on the growth-of-$100 curve.
// `portfolio`/`spy`/`cash` are 2dp-rounded index levels all starting at 100
// on the first charted date; `spy` is null on a ledger date with no SPY close
// (the line connects across it), while `cash` (chained daily fed funds, FRED
// DFF) is null on EVERY point or none — data.py refuses a partial cash line.
// `flow` is that date's net transfer in dollars — marked on the chart but
// deliberately absent from the portfolio index.
export interface EquityCurvePoint {
  date: string;
  portfolio: number;
  spy: number | null;
  cash: number | null;
  flow: number;
}

// equity-curve-only: inception-to-date headline numbers. Derived in Python
// from the UNROUNDED indexes, so read these rather than recomputing them off
// the rounded `curve` points.
export interface EquityCurveSummary {
  twr: number;
  spy: number;
  excess: number;
  // chained daily fed funds (FRED DFF) over the same window; null when
  // fred.db is missing or DFF doesn't cover the window's start.
  cash: number | null;
  ledger_dates: number;
  missing_trading_days: number;
}

// research-reopens-only: held-ticker revisit checkpoints (data.py's
// `checkpoints` list) — a held position's thesis re-check date, distinct
// from the due-date rows already in `columns`/`rows`.
export interface ReopenCheckpoint {
  ticker: string;
  reopen_date: string;
  trigger: string;
  thesis_date: string;
  when_days: number;
  thesis_path: string | null;
}

export interface ScoreHistoryPoint {
  date: string;
  score_sum: number | null;
}

export interface TickerSignal {
  signal: string;
  score: number | null;
  raw_value: number | null;
}

export interface TickerVerdict {
  date: string | null;
  verdict: string | null;
  thesis_path: string | null;
}

export interface TickerFill {
  action: string | null;
  side: string | null;
  fill_date: string | null;
  fill_price: number | null;
  quantity: number | null;
  exit_fill_date: string | null;
  exit_fill_price: number | null;
  opinion_score_sum: number | null;
}

export interface TickerPosition {
  quantity: number | null;
  market_value: number | null;
  heat_dollars: number | null;
  heat_pct: number | null;
}

// The candidates-screen row for this symbol plus its on-list trend and the
// ownership call research-ticker recorded — null when the name is not on
// tonight's screen.
export interface TickerCandidate {
  roic: number | null;
  roic5y: number | null;
  fcfYield: number | null;
  revenueGrowth3Y: number | null;
  netDebtEbitda: number | null;
  fScore: number | null;
  rsi: number | null;
  high52ch: number | null;
  verdict: string | null;
  verdictDate: string | null;
  daysOnList: number | null;
  nSightings: number | null;
  fScoreEntry: number | null;
}

// Newest thesis on disk: repo path, verdicts.log grade + reopen trigger, and
// the static markdown file published beside data.json (fetched on demand).
export interface TickerThesis {
  path: string;
  date: string;
  verdict: string | null;
  reopen: string | null;
  file: string;
}

export interface TickerDetail {
  score_history: ScoreHistoryPoint[];
  signals: TickerSignal[];
  verdicts: TickerVerdict[];
  fills: TickerFill[];
  position: TickerPosition | null;
  candidate: TickerCandidate | null;
  thesis: TickerThesis | null;
}

export interface Hero {
  bullets: Bullet[];
}

// glossary: term -> definition (docs/GLOSSARY.md, parsed).
export type Glossary = Record<string, string>;

export interface DashboardDoc {
  schema_version: number;
  generated_at: string;
  edition_date: string;
  snapshot_number: number | null;
  hero: Hero;
  sections: Record<SectionId, Section>;
  tickers: Record<string, TickerDetail>;
  glossary: Glossary;
}
