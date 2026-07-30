import { render, screen } from "@testing-library/react";
import { StatTile } from "./StatTile";

test("renders the value and a label · band caption", () => {
  render(<StatTile tile={{ label: "VIX", value: 14.2, band: "calm", tone: null }} />);
  expect(screen.getByText("14.20")).toBeInTheDocument();
  expect(screen.getByText("VIX · calm")).toBeInTheDocument();
});

test("renders the label alone when there is no band", () => {
  render(<StatTile tile={{ label: "positions", value: 5 }} />);
  expect(screen.getByText("5.00")).toBeInTheDocument();
  expect(screen.getByText("positions")).toBeInTheDocument();
});

test("dashes a missing value", () => {
  render(<StatTile tile={{ label: "sources failed" }} />);
  expect(screen.getByText("—")).toBeInTheDocument();
});

test("renders an optional sparkline slot via children", () => {
  render(
    <StatTile tile={{ label: "regime", value: "risk_on" }}>
      <svg data-testid="spark" />
    </StatTile>,
  );
  expect(screen.getByTestId("spark")).toBeInTheDocument();
});
