import { render, screen } from "@testing-library/react";
import { BarCell } from "./BarCell";
import { MARK_W } from "./geometry";

const usd = (v: number) => `$${v.toFixed(2)}`;

function farX(d: string): number {
  return Math.max(...[...d.matchAll(/[MHA]\s*(?:[\d.]+,[\d.]+ 0 0 [01] )?(-?[\d.]+)/g)].map((m) => Number(m[1])));
}

test("the bar grows from the left edge to value/max of the axis at 70% primary", () => {
  const { container } = render(<BarCell value={25} max={100} format={usd} />);
  const bar = container.querySelector("path.bar-fill");
  expect(bar?.getAttribute("fill")).toBe("var(--primary)");
  expect(bar?.getAttribute("fill-opacity")).toBe("0.7");
  expect(farX(bar?.getAttribute("d") ?? "")).toBeCloseTo(MARK_W / 4, 1);
  expect(screen.getByText("$25.00")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "$25.00" })).toBeInTheDocument();
  expect(container.querySelector("span[title]")?.getAttribute("title")).toBe("$25.00");
});

test("the max value fills the axis; values above it clamp", () => {
  const full = render(<BarCell value={100} max={100} format={usd} />);
  expect(farX(full.container.querySelector("path.bar-fill")?.getAttribute("d") ?? "")).toBeCloseTo(MARK_W, 1);
  const over = render(<BarCell value={250} max={100} format={usd} />);
  expect(farX(over.container.querySelector("path.bar-fill")?.getAttribute("d") ?? "")).toBeCloseTo(MARK_W, 1);
});

test("no scale, zero, or a missing value degrades to text", () => {
  const noMax = render(<BarCell value={25} max={null} format={usd} />);
  expect(noMax.container.querySelector("svg")).toBeNull();
  expect(noMax.container.textContent).toBe("$25.00");
  const zero = render(<BarCell value={0} max={100} format={usd} />);
  expect(zero.container.querySelector("path.bar-fill")).toBeNull();
  expect(zero.container.textContent).toBe("$0.00");
  expect(render(<BarCell value={null} max={100} format={usd} />).container.textContent).toBe("—");
});
