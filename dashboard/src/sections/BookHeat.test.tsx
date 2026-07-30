import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { BookHeat } from "./BookHeat";

const doc = fixture as unknown as DashboardDoc;

test("renders a StatTile per book-heat tile, with its band as the caption", () => {
  render(<BookHeat sec={doc.sections["book-heat"]} glossary={doc.glossary} />);
  expect(screen.getByText("book heat % · comfortable")).toBeInTheDocument();
  expect(screen.getByText("1.20")).toBeInTheDocument();
  expect(screen.getByText("positions")).toBeInTheDocument(); // no band -> plain label
});
