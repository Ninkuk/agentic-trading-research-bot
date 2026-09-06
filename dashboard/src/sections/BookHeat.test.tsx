import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { BookHeat } from "./BookHeat";

const doc = fixture as unknown as DashboardDoc;

test("renders a StatTile per book-heat tile, with its band as the caption", () => {
  render(<BookHeat sec={doc.sections["book-heat"]} glossary={doc.glossary} />);
  expect(screen.getByText("Money at risk on a bad day · of the book · comfortable")).toBeInTheDocument();
  expect(screen.getByText("0.45%")).toBeInTheDocument();
  expect(screen.getByText("Positions")).toBeInTheDocument(); // no band -> plain label
});
