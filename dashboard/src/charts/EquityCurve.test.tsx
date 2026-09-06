// Geometry assertions are only meaningful because useMeasuredWidth falls
// back to an explicit width and ChartContainer runs responsive={false} —
// jsdom measures ResponsiveContainer 0x0 (see RegimeTimeline.test.tsx).
// ResizeObserver itself is stubbed globally in vitest.setup.ts.

import { render, screen } from "@testing-library/react";
import { EquityCurve } from "./EquityCurve";
import type { EquityCurvePoint } from "../types";

const ROWS: EquityCurvePoint[] = [
  { date: "2026-07-31", portfolio: 100.0, spy: 100.0, cash: 100.0 },
  { date: "2026-08-04", portfolio: 109.72, spy: 101.0, cash: 100.04 },
  { date: "2026-08-05", portfolio: 112.5, spy: 101.59, cash: 100.05 },
];

test("renders all three series lines", () => {
  const { container } = render(<EquityCurve rows={ROWS} />);
  // three Line paths (recharts renders .recharts-line per series)
  expect(container.querySelectorAll(".recharts-line").length).toBe(3);
});

test("legend names all series in text tokens", () => {
  render(<EquityCurve rows={ROWS} />);
  expect(screen.getByText("Portfolio")).toBeInTheDocument();
  expect(screen.getByText("SPY")).toBeInTheDocument();
  expect(screen.getByText("Cash (DFF)")).toBeInTheDocument();
});

// data.py's all-or-nothing rule: cash is null on EVERY point or none, so one
// null point is enough to stand in for "no fred.db coverage".
test("omits the cash line and legend when cash is null throughout", () => {
  const noCash = ROWS.map((r) => ({ ...r, cash: null }));
  const { container } = render(<EquityCurve rows={noCash} />);
  expect(container.querySelectorAll(".recharts-line").length).toBe(2);
  expect(screen.queryByText("Cash (DFF)")).toBeNull();
});

test("renders an optional footnote at the end of the legend row", () => {
  render(<EquityCurve rows={ROWS} footnote="19 positions · 44 trading days" />);
  const note = screen.getByText("19 positions · 44 trading days");
  expect(note.closest(".equity-curve-legend")).not.toBeNull();
  expect(note.className).toContain("ml-auto");
});
