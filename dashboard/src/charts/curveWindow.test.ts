import { describe, expect, test } from "vitest";
import type { EquityCurvePoint } from "../types";
import {
  availableRanges,
  bookVerdict,
  CURVE_RANGES,
  rangeCutoff,
  windowCurve,
} from "./curveWindow";

// One close per trading day. Dates are deliberately irregular (a holiday
// gap at 09-07, no weekend rows) so "the close at or before the cutoff"
// is exercised rather than "the point exactly on it".
// `session` is the exporter's index among ALL book trading days; the gaps
// (07-07 → 08-05 is session 1 → 21) are all-cash days the chart skips.
const pt = (
  date: string,
  portfolio: number,
  spy: number,
  cash: number | null = 100,
  session = 0,
): EquityCurvePoint => ({ date, session, portfolio, spy, cash });

const ROWS: EquityCurvePoint[] = [
  pt("2026-07-06", 100, 100, 100, 0),
  pt("2026-07-07", 104, 99.5, 100.01, 1),
  pt("2026-08-05", 108, 103, 100.3, 21),
  pt("2026-08-14", 105, 104, 100.4, 28),
  pt("2026-09-04", 107, 103, 100.6, 43),
  pt("2026-09-08", 106, 102, 100.65, 44),
  pt("2026-10-05", 101, 103.5, 100.95, 63),
  pt("2026-10-09", 103, 104, 101, 67),
  pt("2026-10-12", 105.26, 104.45, 101.01, 68),
];

test("the selector order is Robinhood's", () => {
  expect(CURVE_RANGES).toEqual(["1D", "1W", "1M", "3M", "YTD", "1Y", "ALL"]);
});

describe("rangeCutoff", () => {
  test("measures back from the last charted date, not today", () => {
    expect(rangeCutoff("1W", "2026-10-12")).toBe("2026-10-05");
    expect(rangeCutoff("1M", "2026-10-12")).toBe("2026-09-12");
    expect(rangeCutoff("3M", "2026-10-12")).toBe("2026-07-12");
    expect(rangeCutoff("1Y", "2026-10-12")).toBe("2025-10-12");
  });
  test("YTD is Jan 1 of the last charted date's year", () => {
    expect(rangeCutoff("YTD", "2026-10-12")).toBe("2026-01-01");
  });
  test("month arithmetic clamps to the last day instead of overflowing", () => {
    // Mar 31 − 1M is Feb 28, never "Feb 31" rolling into March.
    expect(rangeCutoff("1M", "2026-03-31")).toBe("2026-02-28");
    expect(rangeCutoff("3M", "2026-05-31")).toBe("2026-02-28");
    expect(rangeCutoff("1Y", "2028-02-29")).toBe("2027-02-28");
  });
  test("1D and ALL have no calendar cutoff", () => {
    expect(rangeCutoff("1D", "2026-10-12")).toBeNull();
    expect(rangeCutoff("ALL", "2026-10-12")).toBeNull();
  });
});

describe("windowCurve", () => {
  test("ALL returns the rows untouched", () => {
    const w = windowCurve(ROWS, "ALL");
    expect(w.rows).toBe(ROWS);
    expect(w.returns.portfolio).toBeCloseTo(0.0526, 6);
    expect(w.returns.spy).toBeCloseTo(0.0445, 6);
    expect(w.returns.cash).toBeCloseTo(0.0101, 6);
  });

  test("1D is the last two closes, rebased to $100 at the earlier one", () => {
    const w = windowCurve(ROWS, "1D");
    expect(w.rows.map((r) => r.date)).toEqual(["2026-10-09", "2026-10-12"]);
    expect(w.rows[0]).toEqual(pt("2026-10-09", 100, 100, 100, 67));
    expect(w.rows[1].portfolio).toBeCloseTo((105.26 / 103) * 100, 2);
    expect(w.returns.portfolio).toBeCloseTo(105.26 / 103 - 1, 6);
    expect(w.returns.spy).toBeCloseTo(104.45 / 104 - 1, 6);
  });

  test("a window starts at the close AT OR BEFORE the cutoff, so a weekend cutoff still spans the full period", () => {
    // 1W from 10-12 cuts at 10-05 — a charted day, so it is the base.
    expect(windowCurve(ROWS, "1W").rows.map((r) => r.date)).toEqual([
      "2026-10-05",
      "2026-10-09",
      "2026-10-12",
    ]);
    // 1M cuts at 09-12 — no row that day; 09-08 is the last close before it.
    expect(windowCurve(ROWS, "1M").rows.map((r) => r.date)).toEqual([
      "2026-09-08",
      "2026-10-05",
      "2026-10-09",
      "2026-10-12",
    ]);
  });

  test("rebased points are 2dp like the exporter's; returns come from the window endpoints", () => {
    const w = windowCurve(ROWS, "1M");
    expect(w.rows[0]).toEqual(pt("2026-09-08", 100, 100, 100, 44));
    expect(w.rows[3].portfolio).toBe(99.3); // 105.26 / 106
    expect(w.rows[3].spy).toBe(102.4); // 104.45 / 102
    expect(w.returns.portfolio).toBeCloseTo(105.26 / 106 - 1, 6);
    expect(w.returns.spy).toBeCloseTo(104.45 / 102 - 1, 6);
    expect(w.returns.cash).toBeCloseTo(101.01 / 100.65 - 1, 6);
  });

  test("a window knows its base date and counts trading days by session, all-cash days included", () => {
    // 1M bases on 09-08 (session 44) and ends 10-12 (session 68): 25 book
    // trading days, counting the base day the way ALL counts its anchor —
    // though only four of them are charted points.
    const w = windowCurve(ROWS, "1M");
    expect(w.since).toBe("2026-09-08");
    expect(w.tradingDays).toBe(25);
    expect(windowCurve(ROWS, "1D").tradingDays).toBe(2);
    expect(windowCurve(ROWS, "ALL").since).toBe("2026-07-06");
    expect(windowCurve(ROWS, "ALL").tradingDays).toBe(69);
  });

  test("a cutoff before inception falls back to the whole curve", () => {
    expect(windowCurve(ROWS, "YTD").rows.map((r) => r.date)).toEqual(
      ROWS.map((r) => r.date),
    );
    expect(windowCurve(ROWS, "1Y").returns).toEqual(
      windowCurve(ROWS, "ALL").returns,
    );
  });

  test("cash stays null throughout when the exporter shipped none", () => {
    const noCash = ROWS.map((r) => ({ ...r, cash: null }));
    const w = windowCurve(noCash, "1W");
    expect(w.rows.every((r) => r.cash === null)).toBe(true);
    expect(w.returns.cash).toBeNull();
  });
});

describe("availableRanges", () => {
  test("a range is offered only when it shows LESS than ALL", () => {
    // Inception 07-06: 3M (cut 07-12) is inside; YTD and 1Y are not.
    expect([...availableRanges(ROWS)]).toEqual(["1D", "1W", "1M", "3M", "ALL"]);
  });
  test("a book older than a year offers every range", () => {
    // Two closes before the 1Y cutoff (2025-10-12): the base is the later
    // one, so 1Y shows less than ALL. A single pre-cutoff close would not —
    // the window would start at inception and repeat ALL.
    const old = [pt("2024-01-02", 100, 100), pt("2025-06-01", 90, 95), ...ROWS];
    expect([...availableRanges(old)]).toEqual([...CURVE_RANGES]);
    expect([...availableRanges([pt("2024-01-02", 100, 100), ...ROWS])]).not.toContain("1Y");
  });
  test("a curve too short to window offers ALL alone (a two-point 1D IS its ALL)", () => {
    expect([...availableRanges(ROWS.slice(-2))]).toEqual(["ALL"]);
    expect([...availableRanges(ROWS.slice(-1))]).toEqual(["ALL"]);
  });
});

// Mirrors data.py's `_book_verdict`: plain subtraction in percentage
// points, dated from the window's base day, "Even" when it rounds to zero.
describe("bookVerdict", () => {
  test("ahead / behind / even, in points, since the base day", () => {
    expect(bookVerdict(0.0080426, "2026-07-06")).toEqual({
      text: "Ahead of SPY by 0.8 points since Jul 6",
      tone: "on",
    });
    expect(bookVerdict(-0.0165, "2026-09-11")).toEqual({
      text: "Behind SPY by 1.7 points since Sep 11",
      tone: "off",
    });
    expect(bookVerdict(0.0004, "2026-10-09")).toEqual({
      text: "Even with SPY since Oct 9",
      tone: "mid",
    });
    expect(bookVerdict(-0.0004, "2026-12-25").tone).toBe("mid");
  });
});
