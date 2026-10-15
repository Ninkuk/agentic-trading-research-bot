// Robinhood-style range windowing for the growth-of-$100 curve, done on the
// client over the exporter's daily closes. A window is the closes from a
// cutoff to the last charted date, rebased so every series restarts at $100
// at the window's first point; its returns are the window's endpoint
// ratios, which is what the tiles show for a selected range.
//
// The cutoff is measured back from the LAST CHARTED DATE, never from the
// wall clock: the export is nightly, so "1W" on a Monday morning must still
// mean the week before Friday's close. The window's base is the close at or
// before the cutoff (a Sunday cutoff rebases on Friday), so "1M" spans a
// full month rather than starting at the first close inside it.
//
// There is no intraday data, so 1D is the last two closes — the past
// session's change, a single segment on the chart.

import type { EquityCurvePoint, Verdict } from "../types";

export type CurveRange = "1D" | "1W" | "1M" | "3M" | "YTD" | "1Y" | "ALL";

export const CURVE_RANGES: readonly CurveRange[] = [
  "1D",
  "1W",
  "1M",
  "3M",
  "YTD",
  "1Y",
  "ALL",
];

export interface CurveReturns {
  portfolio: number;
  spy: number;
  cash: number | null;
}

export interface CurveWindow {
  rows: EquityCurvePoint[];
  returns: CurveReturns;
  // The base day the window is rebased on — the chip's "since".
  since: string;
  // Book trading days from the base day through the last, inclusive (ALL's
  // convention counts its anchor day), by the exporter's `session` index so
  // uncharted all-cash days still count.
  tradingDays: number;
}

const iso = (y: number, m: number, d: number): string =>
  `${y.toString().padStart(4, "0")}-${m.toString().padStart(2, "0")}-${d
    .toString()
    .padStart(2, "0")}`;

const daysInMonth = (y: number, m: number): number =>
  new Date(Date.UTC(y, m, 0)).getUTCDate();

// Calendar-month arithmetic clamped to the target month's last day, so
// Mar 31 − 1M is Feb 28 rather than rolling through into March.
function shiftMonths(date: string, months: number): string {
  const [y, m, d] = date.split("-").map(Number);
  const total = y * 12 + (m - 1) - months;
  const ty = Math.floor(total / 12);
  const tm = (total % 12) + 1;
  return iso(ty, tm, Math.min(d, daysInMonth(ty, tm)));
}

function shiftDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d - days));
  return iso(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate());
}

/** The calendar cutoff for a range, or null for the two ranges that are
 * defined by point count (1D) or by having none (ALL). */
export function rangeCutoff(range: CurveRange, lastDate: string): string | null {
  switch (range) {
    case "1W":
      return shiftDays(lastDate, 7);
    case "1M":
      return shiftMonths(lastDate, 1);
    case "3M":
      return shiftMonths(lastDate, 3);
    case "YTD":
      return `${lastDate.slice(0, 4)}-01-01`;
    case "1Y":
      return shiftMonths(lastDate, 12);
    default:
      return null;
  }
}

// Index of the window's base point: the last close at or before the cutoff.
// 0 means the window is the whole curve.
function baseIndex(rows: EquityCurvePoint[], range: CurveRange): number {
  if (rows.length === 0) return 0;
  if (range === "1D") return Math.max(0, rows.length - 2);
  const cutoff = rangeCutoff(range, rows[rows.length - 1].date);
  if (cutoff === null) return 0;
  let base = 0;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].date <= cutoff) base = i;
    else break;
  }
  return base;
}

const round2 = (v: number): number => Math.round(v * 100) / 100;

export function windowCurve(
  rows: EquityCurvePoint[],
  range: CurveRange,
): CurveWindow {
  const base = baseIndex(rows, range);
  const first = rows[base];
  const last = rows[rows.length - 1];
  if (!first || !last) {
    return {
      rows,
      returns: { portfolio: 0, spy: 0, cash: null },
      since: "",
      tradingDays: 0,
    };
  }
  const hasCash = first.cash !== null && last.cash !== null;
  const returns: CurveReturns = {
    portfolio: last.portfolio / first.portfolio - 1,
    spy: last.spy / first.spy - 1,
    cash: hasCash ? (last.cash as number) / (first.cash as number) - 1 : null,
  };
  const since = first.date;
  const tradingDays = last.session - first.session + 1;
  if (base === 0) return { rows, returns, since, tradingDays };
  const rebased = rows.slice(base).map((r) => ({
    date: r.date,
    session: r.session,
    portfolio: round2((r.portfolio / first.portfolio) * 100),
    spy: round2((r.spy / first.spy) * 100),
    cash:
      hasCash && r.cash !== null
        ? round2((r.cash / (first.cash as number)) * 100)
        : null,
  }));
  return { rows: rebased, returns, since, tradingDays };
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** The header chip for a window — mirrors data.py's `_book_verdict`: plain
 * subtraction in percentage points ("ahead by 4.8 points", never a ratio),
 * dated from the window's base day, "Even" when it rounds to zero. */
export function bookVerdict(excess: number, since: string): Verdict {
  const [, m, d] = since.split("-").map(Number);
  const when = `since ${MONTHS[m - 1]} ${d}`;
  const pts = Math.abs(excess) * 100;
  if (Math.round(pts * 10) === 0) return { text: `Even with SPY ${when}`, tone: "mid" };
  const word = excess > 0 ? "Ahead of" : "Behind";
  return {
    text: `${word} SPY by ${pts.toFixed(1)} points ${when}`,
    tone: excess > 0 ? "on" : "off",
  };
}

/** The ranges worth offering: those that show strictly less than ALL. A
 * range reaching back before inception would repeat ALL, so it stays
 * disabled until the book has the history. */
export function availableRanges(rows: EquityCurvePoint[]): Set<CurveRange> {
  return new Set(
    CURVE_RANGES.filter((r) => r === "ALL" || baseIndex(rows, r) > 0),
  );
}
