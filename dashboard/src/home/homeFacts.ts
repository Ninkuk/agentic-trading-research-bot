// What the home page says, derived from sections the exporter already
// ships — nothing here is exported twice. Every fact is nullable: a
// missing, empty, or errored section yields null and the page omits or
// degrades that line rather than inventing a zero. The reading horizon is
// 21 trading days, the scorer's standard (candidate-efficacy grades at
// 21/63), pinned by filtering rows rather than trusting a tile whose
// horizon is "longest matured".

import type { BestCall, DashboardDoc, EquityCurvePoint, LastRun, Row, Section, Verdict } from "../types";

export const GRADE_HORIZON = 21;

function live(sec: Section | undefined): Section | null {
  return sec && !sec.error ? sec : null;
}

function rows(sec: Section | undefined): Row[] {
  return live(sec)?.rows ?? [];
}

export interface ResearchCounts {
  theses: number;
  passes: number;
  buys: number;
  sound: number;
  flawed: number;
  unproven: number;
}

/** Call and attack-verdict tallies over every researched name. */
export function researchCounts(doc: DashboardDoc): ResearchCounts | null {
  const r = rows(doc.sections["research"]);
  if (r.length === 0) return null;
  const count = (key: string, value: string) =>
    r.filter((row) => String(row[key] ?? "").toUpperCase() === value).length;
  return {
    theses: r.length,
    passes: count("call", "PASS"),
    buys: count("call", "BUY"),
    sound: count("verdict", "SOUND"),
    flawed: count("verdict", "FLAWED"),
    unproven: count("verdict", "UNPROVEN"),
  };
}

export interface NewestThesis {
  ticker: string;
  date: string;
  call: string;
  verdict: string | null;
}

/** The research row with the latest `thesis_date`. */
export function newestThesis(doc: DashboardDoc): NewestThesis | null {
  let best: Row | null = null;
  for (const row of rows(doc.sections["research"])) {
    if (typeof row.thesis_date !== "string" || typeof row.ticker !== "string") continue;
    if (!best || row.thesis_date > String(best.thesis_date)) best = row;
  }
  if (!best) return null;
  return {
    ticker: String(best.ticker),
    date: String(best.thesis_date),
    call: String(best.call ?? "").toLowerCase(),
    verdict: typeof best.verdict === "string" ? best.verdict.toLowerCase() : null,
  };
}

/** The matured buy call that beat SPY by the most, as the exporter ranked
 * it over the whole view; the frontend never re-ranks the capped rows. */
export function bestCall(doc: DashboardDoc): BestCall | null {
  const sec = live(doc.sections["research-verdict-outcomes"]);
  const b = sec?.best_call;
  if (!b || typeof b.symbol !== "string" || typeof b.excess !== "number") return null;
  return b;
}

/** The first night the regime was called: the timeline's earliest date. */
export function firstNight(doc: DashboardDoc): string | null {
  const rows = live(doc.sections["regime-timeline"])?.rows ?? [];
  let first: string | null = null;
  for (const r of rows) {
    if (typeof r.date === "string" && (first === null || r.date < first)) first = r.date;
  }
  return first;
}

/** Nights the regime has been called, from the timeline's row count. */
export function nightsCalled(doc: DashboardDoc): number | null {
  const sec = live(doc.sections["regime-timeline"]);
  const n = sec?.total ?? sec?.rows?.length ?? 0;
  return n > 0 ? n : null;
}

/** Research calls graded at the reading horizon: the calibration bins' n. */
export function callsGraded(doc: DashboardDoc): number | null {
  const n = rows(doc.sections["research-calibration"])
    .filter((r) => r.horizon === GRADE_HORIZON)
    .reduce((acc, r) => acc + (typeof r.n === "number" ? r.n : 0), 0);
  return n > 0 ? n : null;
}

export interface HitRate {
  rate: number;
  n: number;
}

/** Buy or pass calls right at the reading horizon. */
export function callHitRate(doc: DashboardDoc, call: "buy" | "pass"): HitRate | null {
  const row = rows(doc.sections["research-filter"]).find(
    (r) => String(r.verdict).toLowerCase() === call && r.horizon === GRADE_HORIZON,
  );
  if (!row || typeof row.hit_rate !== "number" || typeof row.n !== "number") return null;
  return { rate: row.hit_rate, n: row.n };
}

export interface Calibration {
  verdict: Verdict;
  forecastError: string | null;
  baseRate: string | null;
}

/** Said-vs-won verdict plus the forecast-error tile, when both exist. */
export function calibration(doc: DashboardDoc): Calibration | null {
  const sec = live(doc.sections["research-calibration"]);
  if (!sec?.verdict) return null;
  const tile = sec.tiles?.find((t) => /forecast error/i.test(t.label));
  const base = tile?.band ? /scores ([\d.]+)/.exec(tile.band)?.[1] : undefined;
  return {
    verdict: sec.verdict,
    forecastError: tile ? String(tile.value) : null,
    baseRate: base ?? null,
  };
}

export interface UnprovenSignals {
  unproven: number;
  total: number;
}

/** Distinct signals, and how many are unproven at every horizon they carry. */
export function unprovenSignals(doc: DashboardDoc): UnprovenSignals | null {
  const byId = new Map<string, boolean>();
  for (const r of rows(doc.sections["signal-recommendations"])) {
    const id = String(r.signal_id ?? "");
    if (!id) continue;
    const proven = String(r.recommendation ?? "") !== "insufficient evidence";
    byId.set(id, (byId.get(id) ?? false) || proven);
  }
  if (byId.size === 0) return null;
  let unproven = 0;
  for (const proven of byId.values()) if (!proven) unproven += 1;
  return { unproven, total: byId.size };
}

export interface Record {
  rows: EquityCurvePoint[];
  verdict: Verdict | null;
  picks: string;
  spy: string;
  cash: string | null;
  since: string;
  tradingDays: number;
}

/** The growth-of-$100 curve with the exporter's own figures (never recomputed). */
export function record(doc: DashboardDoc): Record | null {
  const sec = live(doc.sections["equity-curve"]);
  if (!sec?.curve || sec.curve.length < 2 || !sec.curve_summary) return null;
  const tile = (re: RegExp) => sec.tiles?.find((t) => re.test(t.label));
  const picks = tile(/picks/i);
  const spy = tile(/^spy$/i);
  if (!picks || !spy) return null;
  const cash = tile(/^cash/i);
  return {
    rows: sec.curve,
    verdict: sec.verdict ?? null,
    picks: String(picks.value),
    spy: String(spy.value),
    cash: cash ? String(cash.value) : null,
    since: sec.curve[0].date,
    tradingDays: sec.curve_summary.trading_days,
  };
}

/** The night's job runs as the exporter replayed them, in schedule order. */
export function lastRuns(doc: DashboardDoc): LastRun[] {
  const runs = live(doc.sections["health"])?.last_runs ?? [];
  return runs.filter((r) => typeof r.command === "string" && r.command !== "");
}

/** One job's run, by its launchd name. */
export function lastRunOf(doc: DashboardDoc, job: string): LastRun | null {
  return lastRuns(doc).find((r) => r.job === job) ?? null;
}

export interface Driver {
  label: string;
  value: string;
  band: string | null;
}

/** The regime's watched inputs with tonight's reading and band word. */
export function drivers(doc: DashboardDoc): Driver[] {
  const tiles = live(doc.sections["macro-drivers"])?.tiles ?? [];
  return tiles
    .filter((t) => t.value !== undefined && t.value !== null)
    .map((t) => ({ label: t.label, value: String(t.value), band: t.band ?? null }));
}

/** The "In one sentence" line a thesis opens with, out of its markdown:
 * the `> **In one sentence:** …` callout, joined across its wrapped
 * blockquote lines. Null when the thesis has no such line. */
export function thesisOneLiner(md: string): string | null {
  const lines = md.split("\n");
  const start = lines.findIndex((l) => /\*\*In one sentence:\*\*/.test(l));
  if (start < 0) return null;
  const parts: string[] = [];
  for (let i = start; i < lines.length; i += 1) {
    const l = lines[i];
    if (!l.startsWith(">")) break;
    const body = l.replace(/^>\s?/, "").trim();
    if (i > start && (body === "" || body.startsWith("[!") || body.startsWith("**"))) break;
    parts.push(body);
  }
  const text = parts.join(" ").replace(/\*\*In one sentence:\*\*\s*/, "").replace(/\s+/g, " ").trim();
  return text || null;
}

export interface LastNight {
  jobsRan: number | null;
  regime: string | null;
  tickersScored: number | null;
  candidates: number | null;
  callsGraded: number | null;
  thesis: NewestThesis | null;
}

/** Each step of the nightly run with its live output, for the timeline. */
export function lastNight(doc: DashboardDoc): LastNight {
  const health = live(doc.sections["health"]);
  const jobs = health?.tiles?.find((t) => /jobs that ran/i.test(t.label));
  const scorecard = live(doc.sections["scorecard"]);
  const scored = scorecard?.total ?? scorecard?.rows?.length ?? 0;
  const candidates = live(doc.sections["candidates"]);
  const listed = candidates?.total ?? candidates?.rows?.length ?? 0;
  return {
    jobsRan: typeof jobs?.value === "number" ? jobs.value : null,
    regime: live(doc.sections["regime"])?.verdict?.text ?? null,
    tickersScored: scored > 0 ? scored : null,
    candidates: listed > 0 ? listed : null,
    callsGraded: callsGraded(doc),
    thesis: newestThesis(doc),
  };
}
