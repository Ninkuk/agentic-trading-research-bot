import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Pending } from "./Pending";

const doc = fixture as unknown as DashboardDoc;

test('shows "showing N of TOTAL" using the row count actually rendered and the full view total', () => {
  const sec = doc.sections.pending;
  render(<Pending sec={sec} glossary={doc.glossary} />);
  expect(screen.getByText(`showing ${sec.rows?.length} of ${sec.total}`)).toBeInTheDocument();
});
