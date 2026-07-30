import { render } from "@testing-library/react";
import { tokens } from "../theme";
import { Sparkline } from "./Sparkline";

const POINTS = [
  { date: "2026-07-01", value: 10 },
  { date: "2026-07-02", value: 12 },
  { date: "2026-07-03", value: 11 },
];

test("renders nothing for fewer than 2 usable points", () => {
  const { container: empty } = render(<Sparkline points={[]} />);
  expect(empty.firstChild).toBeNull();

  const { container: one } = render(<Sparkline points={[{ date: "2026-07-01", value: 10 }]} />);
  expect(one.firstChild).toBeNull();

  const { container: allNull } = render(
    <Sparkline
      points={[
        { date: "2026-07-01", value: null },
        { date: "2026-07-02", value: null },
      ]}
    />,
  );
  expect(allNull.firstChild).toBeNull();
});

test("renders a single 2px line for >= 2 usable points, token-colored", () => {
  const { container } = render(<Sparkline points={POINTS} tone="up" />);
  const line = container.querySelector(".spark-line path");
  expect(line).toBeInTheDocument();
  expect(line).toHaveAttribute("stroke", tokens.up);
  expect(line).toHaveAttribute("stroke-width", "2");
});

test("defaults to the neutral hold token when no tone is given", () => {
  const { container } = render(<Sparkline points={POINTS} />);
  const line = container.querySelector(".spark-line path");
  expect(line).toHaveAttribute("stroke", tokens.hold);
});
