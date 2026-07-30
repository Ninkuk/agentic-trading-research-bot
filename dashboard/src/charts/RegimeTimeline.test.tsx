import { fireEvent, render } from "@testing-library/react";
import { tokens } from "../theme";
import { RegimeTimeline, type RegimeTimelineRow } from "./RegimeTimeline";

const ROWS: RegimeTimelineRow[] = [
  { date: "2026-07-01", regime: "risk_on", vix: 13.1 },
  { date: "2026-07-02", regime: "risk_on", vix: 12.8 },
  { date: "2026-07-03", regime: "risk_off", vix: 21.4 },
  { date: "2026-07-04", regime: "mixed", vix: 17.0 },
  { date: "2026-07-05", regime: null, vix: null },
];

const MANY_ROWS: RegimeTimelineRow[] = Array.from({ length: 20 }, (_, i) => ({
  date: `2026-07-${String(i + 1).padStart(2, "0")}`,
  regime: i % 2 === 0 ? "risk_on" : "risk_off",
  vix: 10 + i,
}));

test("strip renders one cell per row", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  expect(container.querySelectorAll(".strip-cell")).toHaveLength(ROWS.length);
});

test("strip cells wear token-only colors by regime, gray midpoint for anything else", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const cells = container.querySelectorAll(".strip-cell");
  expect(cells[0]).toHaveStyle({ backgroundColor: tokens.up }); // risk_on
  expect(cells[2]).toHaveStyle({ backgroundColor: tokens.down }); // risk_off
  expect(cells[3]).toHaveStyle({ backgroundColor: tokens.hold }); // mixed
  expect(cells[4]).toHaveStyle({ backgroundColor: tokens.hold }); // null/unknown
});

test("each cell carries a date + regime + vix tooltip title", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const first = container.querySelectorAll(".strip-cell")[0];
  expect(first).toHaveAttribute("title", "2026-07-01 · risk_on · VIX 13.1");
});

test("empty rows degrades to a no-data note instead of an empty chart", () => {
  const { container, getByText } = render(<RegimeTimeline rows={[]} />);
  expect(getByText("no data")).toBeInTheDocument();
  expect(container.querySelector(".strip-cell")).toBeNull();
});

test("VIX line renders token-colored", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const line = container.querySelector(".regime-vix-line path");
  expect(line).toHaveAttribute("stroke", tokens.hold);
});

test("Brush is present and wears token colors", () => {
  const { container } = render(<RegimeTimeline rows={ROWS} />);
  const brush = container.querySelector(".recharts-brush");
  expect(brush).toBeInTheDocument();
  const brushRect = brush?.querySelector("rect");
  expect(brushRect).toHaveAttribute("stroke", tokens.brass);
  const traveller = brush?.querySelector(".recharts-brush-traveller rect");
  expect(traveller).toHaveAttribute("fill", tokens.brass);
});

test("dragging the brush's right traveller filters the strip layer too", () => {
  const { container } = render(<RegimeTimeline rows={MANY_ROWS} width={400} height={200} />);
  expect(container.querySelectorAll(".strip-cell")).toHaveLength(MANY_ROWS.length);

  const rightTraveller = container.querySelectorAll(".recharts-brush-traveller")[1];
  const handleRect = rightTraveller.querySelector("rect")!;
  const x = Number(handleRect.getAttribute("x"));
  const y = Number(handleRect.getAttribute("y"));
  fireEvent.mouseDown(rightTraveller, { clientX: x, clientY: y });
  fireEvent(window, new MouseEvent("mousemove", { bubbles: true, clientX: x - 100 }));
  fireEvent(window, new MouseEvent("mouseup", { bubbles: true }));

  // Dragging the end traveller left narrows the window; the strip must
  // shrink to match, not stay pinned at the full row count.
  expect(container.querySelectorAll(".strip-cell").length).toBeLessThan(MANY_ROWS.length);
});
