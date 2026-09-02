import { render, screen } from "@testing-library/react";
import { RangeCell } from "./RangeCell";
import { MARK_W, rangeX } from "./geometry";

test("the dot for rate 0.5 sits mid-axis, the whisker spans lo..hi, the tick is dashed", () => {
  const { container } = render(<RangeCell rate={0.5} lo={0.25} hi={0.75} tick={0.4} />);
  const dot = container.querySelector("circle.range-dot");
  expect(Number(dot?.getAttribute("cx"))).toBeCloseTo(MARK_W / 2, 5);
  const whisker = container.querySelector("line.range-whisker");
  expect(Number(whisker?.getAttribute("x1"))).toBeCloseTo(rangeX(0.25), 5);
  expect(Number(whisker?.getAttribute("x2"))).toBeCloseTo(rangeX(0.75), 5);
  expect(Number(whisker?.getAttribute("x1"))).toBeLessThan(Number(dot?.getAttribute("cx")));
  const tick = container.querySelector("line.range-tick");
  expect(Number(tick?.getAttribute("x1"))).toBeCloseTo(rangeX(0.4), 5);
  expect(tick?.getAttribute("stroke-dasharray")).toBe("2 2");
  // A ring under the dot in the surface color, not a stroke around it.
  expect(container.querySelector("circle.range-ring")?.getAttribute("fill")).toBe("var(--card)");
});

test("rate stays visible as text; CI digits live in the title and the img label", () => {
  const { container } = render(<RangeCell rate={0.38} lo={0.08} hi={0.82} tick={0.5} />);
  expect(screen.getByText("38%")).toBeInTheDocument();
  expect(container.querySelector("span[title]")?.getAttribute("title")).toBe("38%, CI 8–82%, beats 50%");
  expect(screen.getByRole("img", { name: "38%, CI 8–82%, beats 50%" })).toBeInTheDocument();
  expect(container.querySelector("span.font-mono")?.textContent).toBe("38%");
});

test("no tick line without a numeric tick; no CI means plain text; no rate means a dash", () => {
  const { container } = render(<RangeCell rate={0.5} lo={0.1} hi={0.9} tick={null} />);
  expect(container.querySelector("line.range-tick")).toBeNull();
  const plain = render(<RangeCell rate={0.5} lo={null} hi={0.9} />);
  expect(plain.container.querySelector("svg")).toBeNull();
  expect(plain.container.textContent).toBe("50%");
  const dash = render(<RangeCell rate={null} lo={0.1} hi={0.9} />);
  expect(dash.container.textContent).toBe("—");
});
