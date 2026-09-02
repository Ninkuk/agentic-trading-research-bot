import { render, screen } from "@testing-library/react";
import { DivergingCell } from "./DivergingCell";
import { MARK_H, MARK_W, maxAbs, roundedEndBar } from "./geometry";

const CENTER = MARK_W / 2;

/** Every x in a path's absolute commands. */
function xs(d: string): number[] {
  return [...d.matchAll(/[MHA]\s*(?:[\d.]+,[\d.]+ 0 0 [01] )?(-?[\d.]+)/g)].map((m) => Number(m[1]));
}

test("a positive value bars right of the centre line with a 2px gap, tone-up fill", () => {
  const { container } = render(<DivergingCell value={0.02} max={0.04} />);
  const bar = container.querySelector("path.diverging-bar");
  expect(bar?.getAttribute("fill")).toBe("var(--tone-up)");
  const d = bar?.getAttribute("d") ?? "";
  expect(Math.min(...xs(d))).toBeCloseTo(CENTER + 2, 1);
  // Half of max → half of the available half-axis.
  expect(Math.max(...xs(d))).toBeCloseTo(CENTER + 2 + (CENTER - 2) / 2, 1);
});

test("a negative value bars left of the centre line, tone-down fill, label on the left", () => {
  const { container } = render(<DivergingCell value={-0.04} max={0.04} />);
  const bar = container.querySelector("path.diverging-bar");
  expect(bar?.getAttribute("fill")).toBe("var(--tone-down)");
  const d = bar?.getAttribute("d") ?? "";
  expect(Math.max(...xs(d))).toBeCloseTo(CENTER - 2, 1);
  expect(Math.min(...xs(d))).toBeCloseTo(0, 1);
  const slots = container.querySelectorAll("span.diverging-cell > span");
  expect(slots[0].textContent).toBe("−4.0%");
  expect(slots[1].textContent).toBe("");
});

test("width scales with max: the same value is half as long under a doubled max", () => {
  const narrow = render(<DivergingCell value={0.01} max={0.02} />);
  const wide = render(<DivergingCell value={0.01} max={0.04} />);
  const len = (c: HTMLElement) => {
    const d = c.querySelector("path.diverging-bar")?.getAttribute("d") ?? "";
    return Math.max(...xs(d)) - Math.min(...xs(d));
  };
  expect(len(wide.container)).toBeCloseTo(len(narrow.container) / 2, 1);
});

test("the label never wears the tone; the digits sit in the title and img label", () => {
  const { container } = render(<DivergingCell value={0.012} max={0.05} />);
  const label = screen.getByText("+1.2%");
  expect(label.className).not.toMatch(/tag-|tone/);
  expect(container.querySelector("span[title]")?.getAttribute("title")).toBe("+1.2%");
  expect(screen.getByRole("img", { name: "+1.2%" })).toBeInTheDocument();
});

test("zero draws no bar; a missing max or value falls back to text", () => {
  const zero = render(<DivergingCell value={0} max={0.05} />);
  expect(zero.container.querySelector("path.diverging-bar")).toBeNull();
  expect(zero.container.textContent).toBe("0.0%");
  const noMax = render(<DivergingCell value={0.012} max={null} />);
  expect(noMax.container.querySelector("svg")).toBeNull();
  expect(noMax.container.textContent).toBe("+1.2%");
  expect(render(<DivergingCell value={null} max={1} />).container.textContent).toBe("—");
});

test("maxAbs needs three finite values and a non-zero max", () => {
  expect(maxAbs([0.1, -0.3, 0.2])).toBe(0.3);
  expect(maxAbs([0.1, null, 0.2])).toBeNull();
  expect(maxAbs([0, 0, 0])).toBeNull();
  expect(maxAbs([1, Number.NaN, 2, "3"])).toBeNull();
});

test("roundedEndBar is square at the baseline and rounded only at the far end", () => {
  const d = roundedEndBar(10, 50, MARK_H);
  expect(d.startsWith("M10.0,0 H46.0 A4,4")).toBe(true);
  expect(d.endsWith("H10.0 Z")).toBe(true);
  // Too short to round: a plain rectangle.
  expect(roundedEndBar(10, 12, MARK_H)).toBe("M10.0,0 H12.0 V14.0 H10.0 Z");
});
