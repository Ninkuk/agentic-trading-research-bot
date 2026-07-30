import { render, screen } from "@testing-library/react";
import { tokens } from "../theme";
import { ScoreBar } from "./ScoreBar";

test("renders the signed score as visible text (color is never the only channel)", () => {
  const { rerender } = render(<ScoreBar value={4} bullish={3} bearish={1} max={4} />);
  expect(screen.getByText("+4")).toBeInTheDocument();

  rerender(<ScoreBar value={-2} bullish={1} bearish={3} max={4} />);
  expect(screen.getByText("−2")).toBeInTheDocument();

  rerender(<ScoreBar value={0} bullish={2} bearish={2} max={4} />);
  expect(screen.getByText("0")).toBeInTheDocument();
});

test("positive score bars right (up) in the token color, text tone matches", () => {
  const { container } = render(<ScoreBar value={4} bullish={3} bearish={1} max={4} />);
  const mark = container.querySelector(".score-bar-mark");
  expect(mark).toHaveStyle({ backgroundColor: tokens.up });
  expect(mark).toHaveStyle({ left: "50%" });
  expect(screen.getByText("+4")).toHaveClass("up");
});

test("negative score bars left (down) in the token color, text tone matches", () => {
  const { container } = render(<ScoreBar value={-2} bullish={1} bearish={3} max={4} />);
  const mark = container.querySelector(".score-bar-mark");
  expect(mark).toHaveStyle({ backgroundColor: tokens.down });
  expect(mark).toHaveStyle({ right: "50%" });
  expect(screen.getByText("−2")).toHaveClass("down");
});

test("bar fill scales with |value| / max, clamped at the track edge", () => {
  const { container: half } = render(<ScoreBar value={2} bullish={2} bearish={0} max={4} />);
  expect(half.querySelector(".score-bar-mark")).toHaveStyle({ width: "25%" });

  const { container: over } = render(<ScoreBar value={10} bullish={4} bearish={0} max={4} />);
  expect(over.querySelector(".score-bar-mark")).toHaveStyle({ width: "50%" });
});
