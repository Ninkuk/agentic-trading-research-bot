import { render } from "@testing-library/react";
import { tokens } from "../theme";
import { RegimeTimeline, type RegimeTimelineRow } from "./RegimeTimeline";

const ROWS: RegimeTimelineRow[] = [
  { date: "2026-07-01", regime: "risk_on", vix: 13.1 },
  { date: "2026-07-02", regime: "risk_on", vix: 12.8 },
  { date: "2026-07-03", regime: "risk_off", vix: 21.4 },
  { date: "2026-07-04", regime: "mixed", vix: 17.0 },
  { date: "2026-07-05", regime: null, vix: null },
];

test("VIX area renders in the chart token", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const curve = container.querySelector(".regime-vix-line .recharts-area-curve");
  expect(curve).toHaveAttribute("stroke", "var(--chart-2)");
});

test("per-night dots wear the regime's tone, gray-amber midpoint for anything else", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const dots = container.querySelectorAll(".regime-dot");
  // One dot per non-null VIX row (the null 07-05 row draws no dot).
  expect(dots).toHaveLength(4);
  expect(dots[0]).toHaveAttribute("fill", tokens.up); // risk_on
  expect(dots[2]).toHaveAttribute("fill", tokens.down); // risk_off
  expect(dots[3]).toHaveAttribute("fill", tokens.hold); // mixed
});

test("empty rows degrades to a no-data note instead of an empty chart", () => {
  const { container, getByText } = render(<RegimeTimeline rows={[]} />);
  expect(getByText("no data")).toBeInTheDocument();
  expect(container.querySelector("svg")).toBeNull();
});

test("the dot-color caption renders under the chart", () => {
  const { getByText } = render(<RegimeTimeline rows={ROWS} />);
  expect(getByText(/dot color = that night's regime verdict/i)).toBeInTheDocument();
});
