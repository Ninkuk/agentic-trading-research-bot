import { render, screen } from "@testing-library/react";
import { tokens } from "../theme";
import { VerdictChip } from "./VerdictChip";

test("renders verdict text for every tone", () => {
  const { rerender } = render(<VerdictChip verdict={{ text: "Risk-on", tone: "on" }} />);
  expect(screen.getByText("Risk-on")).toBeInTheDocument();

  rerender(<VerdictChip verdict={{ text: "Risk-off", tone: "off" }} />);
  expect(screen.getByText("Risk-off")).toBeInTheDocument();

  rerender(<VerdictChip verdict={{ text: "Mixed", tone: "mid" }} />);
  expect(screen.getByText("Mixed")).toBeInTheDocument();
});

test("tone maps to the validated palette token color", () => {
  const { rerender } = render(<VerdictChip verdict={{ text: "Risk-on", tone: "on" }} />);
  expect(screen.getByText("Risk-on")).toHaveStyle({ color: tokens.up });

  rerender(<VerdictChip verdict={{ text: "Risk-off", tone: "off" }} />);
  expect(screen.getByText("Risk-off")).toHaveStyle({ color: tokens.down });

  rerender(<VerdictChip verdict={{ text: "Mixed", tone: "mid" }} />);
  expect(screen.getByText("Mixed")).toHaveStyle({ color: tokens.muted });
});
