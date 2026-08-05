import { render } from "@testing-library/react";
import { KpiSpark, type KpiSparkPoint } from "./KpiSpark";

function points(values: (number | null)[]): KpiSparkPoint[] {
  return values.map((value, i) => ({ date: `2026-07-${String(i + 1).padStart(2, "0")}`, value }));
}

test("a 2-point series drops the chart (DESIGN_MEMORY: no tiny 2-point sparklines)", () => {
  const { container } = render(<KpiSpark label="VIX" points={points([14.2, 15.1])} />);
  expect(container.firstChild).toBeNull();
});

test("nulls thinning a longer series to 2 usable points also drop the chart", () => {
  const { container } = render(<KpiSpark label="VIX" points={points([14.2, null, 15.1, null])} />);
  expect(container.firstChild).toBeNull();
});

test("3 usable points render a chart", () => {
  const { container } = render(<KpiSpark label="VIX" points={points([14.2, 15.1, 13.9])} />);
  expect(container.querySelector("[data-chart]")).toBeInTheDocument();
});
