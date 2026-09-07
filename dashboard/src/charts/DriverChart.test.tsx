import { render } from "@testing-library/react";
import { DriverChart, type DriverPoint } from "./DriverChart";
import { driverDomain } from "./driverDomain";

function points(values: (number | null)[]): DriverPoint[] {
  return values.map((value, i) => ({ date: `2026-07-${String(i + 1).padStart(2, "0")}`, value }));
}

const VIX_EDGES = [
  { value: 15, below: "calm", above: "normal" },
  { value: 20, below: "normal", above: "nervous" },
  { value: 30, below: "nervous", above: "stressed" },
];

test("a 2-point series drops the chart (DESIGN_MEMORY: no tiny 2-point sparklines)", () => {
  const { container } = render(<DriverChart label="VIX" points={points([14.2, 15.1])} />);
  expect(container.firstChild).toBeNull();
});

test("draws cutoffs inside the range, plus the nearest outside one within half a range", () => {
  // VIX 13–19 (span 6): 15 is inside, 20 is 1 above (≤ 3) and drawn, 30 is
  // 11 above and left out — it would flatten the series into a ribbon.
  const { domain, drawn } = driverDomain([13, 14, 19, 15], VIX_EDGES);
  expect(drawn.map((t) => t.value)).toEqual([15, 20]);
  expect(domain[0]).toBeLessThan(13);
  expect(domain[1]).toBeGreaterThan(20);
});

test("only the nearest outside cutoff per side is considered", () => {
  // VIX 12–14 (span 2): 15 is 1 above and drawn; 20 is not the nearest.
  expect(driverDomain([12, 13, 14], VIX_EDGES).drawn.map((t) => t.value)).toEqual([15]);
  // VIX 12–13 (span 1): 15 is 2 above (> 0.5) — nothing drawn, domain hugs the data.
  const { domain, drawn } = driverDomain([12, 12.5, 13], VIX_EDGES);
  expect(drawn).toEqual([]);
  expect(domain[1]).toBeLessThan(15);
});

test("a flat series still gets a finite domain", () => {
  const { domain } = driverDomain([14, 14, 14], []);
  expect(domain[0]).toBeLessThan(14);
  expect(domain[1]).toBeGreaterThan(14);
});

test("renders a reference line labelled with the band above the cutoff", () => {
  const { container } = render(
    <DriverChart label="VIX" points={points([13, 14, 19, 15, 14])} thresholds={VIX_EDGES} />,
  );
  const lines = container.querySelectorAll(".driver-threshold");
  expect(lines).toHaveLength(2);
  expect(container.textContent).toContain("normal");
  expect(container.textContent).toContain("nervous");
  expect(container.textContent).not.toContain("stressed");
});

test("date axis shows first, middle and last observation, edge labels anchored inward", () => {
  const { container } = render(<DriverChart label="VIX" points={points([13, 14, 16, 15, 14])} />);
  const ticks = Array.from(
    container.querySelectorAll(".recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value"),
  );
  expect(ticks.map((t) => t.textContent)).toEqual(["Jul 1", "Jul 3", "Jul 5"]);
  expect(ticks.map((t) => t.getAttribute("text-anchor"))).toEqual(["start", "middle", "end"]);
});
