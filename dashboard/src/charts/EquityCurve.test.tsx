// Geometry assertions are only meaningful because useMeasuredWidth falls
// back to an explicit width and ChartContainer runs responsive={false} —
// jsdom measures ResponsiveContainer 0x0 (see RegimeTimeline.test.tsx).
// ResizeObserver itself is stubbed globally in vitest.setup.ts.

import { render, screen } from "@testing-library/react";
import { EquityCurve } from "./EquityCurve";
import type { EquityCurvePoint } from "../types";

const ROWS: EquityCurvePoint[] = [
  { date: "2026-07-31", portfolio: 100.0, spy: 100.0, flow: 0 },
  { date: "2026-08-01", portfolio: 100.2, spy: null, flow: 0 },
  { date: "2026-08-04", portfolio: 103.05, spy: 101.0, flow: 100 },
  { date: "2026-08-05", portfolio: 104.07, spy: 101.59, flow: 0 },
];

test("renders both series lines and a transfer marker", () => {
  const { container } = render(<EquityCurve rows={ROWS} />);
  // two Line paths (recharts renders .recharts-line per series)
  expect(container.querySelectorAll(".recharts-line").length).toBe(2);
  // the flow row renders a reference dot layer
  expect(container.querySelector(".recharts-reference-dot")).not.toBeNull();
});

test("legend names both series in text tokens", () => {
  render(<EquityCurve rows={ROWS} />);
  expect(screen.getByText("Portfolio")).toBeInTheDocument();
  expect(screen.getByText("SPY")).toBeInTheDocument();
});
