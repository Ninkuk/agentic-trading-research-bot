// Geometry assertions are only meaningful because useMeasuredWidth falls
// back to an explicit width and ChartContainer runs responsive={false} —
// jsdom measures ResponsiveContainer 0x0 (see RegimeTimeline.test.tsx).
// ResizeObserver itself is stubbed globally in vitest.setup.ts.

import { render, screen } from "@testing-library/react";
import { EquityCurve } from "./EquityCurve";
import type { EquityCurvePoint } from "../types";

const ROWS: EquityCurvePoint[] = [
  { date: "2026-07-31", session: 0, portfolio: 100.0, spy: 100.0, cash: 100.0 },
  { date: "2026-08-04", session: 1, portfolio: 109.72, spy: 101.0, cash: 100.04 },
  { date: "2026-08-05", session: 2, portfolio: 112.5, spy: 101.59, cash: 100.05 },
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

// A narrow window (1D is a ±0.1% move) spans well under a dollar, so
// whole-dollar ticks all read "$100". Precision follows the plotted span.
test("y-axis ticks stay distinct on a sub-dollar span", () => {
  const tight: EquityCurvePoint[] = [
    { date: "2026-10-09", session: 0, portfolio: 100, spy: 100, cash: 100 },
    { date: "2026-10-12", session: 1, portfolio: 99.96, spy: 99.93, cash: 100.03 },
  ];
  const { container } = render(<EquityCurve rows={tight} />);
  const ticks = [
    ...container.querySelectorAll(
      ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
    ),
  ].map((t) => t.textContent);
  expect(ticks.length).toBeGreaterThan(1);
  expect(new Set(ticks).size).toBe(ticks.length);
  expect(ticks.every((t) => /^\$\d+\.\d{2}$/.test(t ?? ""))).toBe(true);
});

test("y-axis ticks are whole dollars on a wide span", () => {
  const { container } = render(<EquityCurve rows={ROWS} />);
  const ticks = [
    ...container.querySelectorAll(
      ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
    ),
  ].map((t) => t.textContent);
  expect(ticks.every((t) => /^\$\d+$/.test(t ?? ""))).toBe(true);
});

// The range picker is the last thing in the card, under the legend row —
// Robinhood's order is chart, then the row of labels beneath everything.
test("renders the controls slot below the legend row", () => {
  const { container } = render(
    <EquityCurve rows={ROWS} controls={<button>1M</button>} />,
  );
  const legend = container.querySelector(".equity-curve-legend");
  const controls = container.querySelector(".equity-curve-controls");
  expect(controls?.textContent).toBe("1M");
  expect(
    legend!.compareDocumentPosition(controls!) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});
