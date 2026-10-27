import { render, screen } from "@testing-library/react";
import { VerdictChip } from "./VerdictChip";

test("renders verdict text for every tone", () => {
  const { rerender } = render(<VerdictChip verdict={{ text: "Risk-on", tone: "on" }} />);
  expect(screen.getByText("Risk-on")).toBeInTheDocument();

  rerender(<VerdictChip verdict={{ text: "Risk-off", tone: "off" }} />);
  expect(screen.getByText("Risk-off")).toBeInTheDocument();

  rerender(<VerdictChip verdict={{ text: "Mixed", tone: "mid" }} />);
  expect(screen.getByText("Mixed")).toBeInTheDocument();
});

test("tone maps to the tint class, never an inline color", () => {
  // Colors live entirely in the .verdict-chip--{tone} CSS (light AND dark
  // values) — an inline style here once overrode the amber text with gray
  // and produced an unreadable mid chip.
  const { rerender } = render(<VerdictChip verdict={{ text: "Risk-on", tone: "on" }} />);
  expect(screen.getByText("Risk-on")).toHaveClass("verdict-chip--on");
  expect(screen.getByText("Risk-on")).not.toHaveAttribute("style");

  rerender(<VerdictChip verdict={{ text: "Mixed", tone: "mid" }} />);
  expect(screen.getByText("Mixed")).toHaveClass("verdict-chip--mid");
  expect(screen.getByText("Mixed")).not.toHaveAttribute("style");
});

test("a verdict may wrap: a nowrap sentence is the widest thing on a phone", () => {
  render(<VerdictChip verdict={{ text: "Stronger flags did not do better: 20% right vs 45% at 21 days", tone: "off" }} />);
  const chip = screen.getByText(/Stronger flags/);
  expect(chip).toHaveClass("whitespace-normal");
  expect(chip).not.toHaveClass("whitespace-nowrap");
});
