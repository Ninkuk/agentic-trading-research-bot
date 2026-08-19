// Geometry assertions are only meaningful because useMeasuredWidth falls
// back to an explicit width and ChartContainer runs responsive={false} —
// jsdom measures ResponsiveContainer 0x0 (see RegimeTimeline.test.tsx).
// ResizeObserver itself is stubbed globally in vitest.setup.ts.

import { render, screen } from "@testing-library/react";
import { EquityCurve } from "./EquityCurve";
import type { EquityCurvePoint } from "../types";

const ROWS: EquityCurvePoint[] = [
  { date: "2026-07-31", portfolio: 100.0, spy: 100.0, cash: 100.0, flow: 0 },
  { date: "2026-08-01", portfolio: 100.2, spy: null, cash: 100.01, flow: 0 },
  { date: "2026-08-04", portfolio: 103.05, spy: 101.0, cash: 100.04, flow: 100 },
  { date: "2026-08-05", portfolio: 104.07, spy: 101.59, cash: 100.05, flow: 0 },
];

test("renders all three series lines and a transfer marker", () => {
  const { container } = render(<EquityCurve rows={ROWS} />);
  // three Line paths (recharts renders .recharts-line per series)
  expect(container.querySelectorAll(".recharts-line").length).toBe(3);
  // the flow row renders a reference dot layer
  expect(container.querySelector(".recharts-reference-dot")).not.toBeNull();
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
