import { render, screen } from "@testing-library/react";
import { Sparkline } from "./Sparkline";

test("draws one polyline through every point with the last point marked", () => {
  const { container } = render(<Sparkline values={[1, 3, 2, 5]} label="Trend" />);
  const poly = container.querySelector("polyline");
  expect(poly).not.toBeNull();
  expect(poly?.getAttribute("points")?.split(" ")).toHaveLength(4);
  expect(container.querySelector("circle")).not.toBeNull();
  expect(screen.getByRole("img", { name: "Trend: 4 points, 1 → 5" })).toBeInTheDocument();
});

test("a flat series still renders (no divide-by-zero span)", () => {
  const { container } = render(<Sparkline values={[2, 2, 2]} />);
  const pts = container.querySelector("polyline")?.getAttribute("points") ?? "";
  expect(pts).not.toMatch(/NaN/);
});

test("fewer than three finite points is a dash, not a dot", () => {
  const { container } = render(<Sparkline values={[1, Number.NaN, 2]} />);
  expect(container.querySelector("svg")).toBeNull();
  expect(container.textContent).toBe("—");
});
