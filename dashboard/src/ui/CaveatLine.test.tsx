import { render, screen } from "@testing-library/react";
import { CaveatLine } from "./CaveatLine";

test("renders the caveat text", () => {
  render(<CaveatLine text="Nominal and uncorrected across ~48 comparisons." />);
  expect(
    screen.getByText("Nominal and uncorrected across ~48 comparisons."),
  ).toBeInTheDocument();
});
