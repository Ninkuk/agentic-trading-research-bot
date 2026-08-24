import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Candidates } from "./Candidates";

const doc = fixture as unknown as DashboardDoc;

test("symbol cells link to the ticker page", () => {
  render(<Candidates sec={doc.sections.candidates} glossary={doc.glossary} />);
  expect(screen.getByRole("link", { name: "PEGA" })).toHaveAttribute("href", "#/ticker/PEGA");
});
