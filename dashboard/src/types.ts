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

// The five strand groups a section's `kicker` sorts it into (Main.tsx's
// STRANDS, data.py's SECTION_EXPORTERS kicker column). Kept as a real union
// — not a bare `string` — so a hand-authored Section (tests, fixtures the
// Loosen<T> guard checks) gets a compile-time nudge toward a real strand
// name. This can't catch a *live* JSON payload disagreeing at runtime
// (JSON always reads back as plain `string`) — that's what the
// "every fixture section's kicker is a known strand" test in
// fixtures/data.test.ts is for, and why Main.tsx's strand grouping still
// runs a defensive membership check and routes anything unrecognized into
// a trailing "Other" group rather than ever silently dropping it.
export type Kicker = "Macro" | "Signals" | "Research" | "Track record" | "Your book";

// Canonical strand order — the single source Main.tsx, StrandNav, and the
// fixture drift test all read from, so the list can't fork.
export const KICKERS: readonly Kicker[] = ["Macro", "Signals", "Research", "Track record", "Your book"];

// One section of the document (sections[<id>]). A section that failed to
// export degrades to `{ title, kicker, note, error }` only — every other
// field is therefore optional. A healthy section carries some subset of
// verdict/tiles/columns/rows/text_lines depending on its exporter (see
// data.py's per-section return shapes: tile sections like `regime`/
// `book-heat`, table sections like `scorecard`/`signal-efficacy`, and the
// text-only `plan-004-scorecard`).
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
  // research-reopens-only:
  dated?: number;
  events?: number;
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

export interface TickerDetail {
  score_history: ScoreHistoryPoint[];
  signals: TickerSignal[];
  verdicts: TickerVerdict[];
  fills: TickerFill[];
  position: TickerPosition | null;
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
