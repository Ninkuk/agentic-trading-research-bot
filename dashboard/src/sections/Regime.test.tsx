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
  // The raw `risk_on` id humanizes at the render boundary (StatTile).
  expect(screen.getByText("Risk on")).toBeInTheDocument();
  expect(screen.getByText("14.20")).toBeInTheDocument();
  expect(screen.getByText("10y–2y spread")).toBeInTheDocument();
});
