import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Regime } from "./Regime";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
});

test("renders regime tiles and the drivers table", () => {
  render(<Regime sec={doc.sections.regime} glossary={doc.glossary} />);
  // The exporter spells the mood the glossary's way ("risk-on"), never the
  // raw `risk_on` id.
  expect(screen.getByText(/risk.on/i)).toBeInTheDocument();
  expect(screen.getByText("16.10")).toBeInTheDocument();
  expect(screen.getByText("10y–2y spread")).toBeInTheDocument();
});
