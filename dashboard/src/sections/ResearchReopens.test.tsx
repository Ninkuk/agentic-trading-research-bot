import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import { REPO_URL } from "../constants";
import type { DashboardDoc } from "../types";
import { ResearchReopens } from "./ResearchReopens";

const doc = fixture as unknown as DashboardDoc;

test("links a dated row's ticker to its thesis doc on GitHub", () => {
  render(<ResearchReopens sec={doc.sections["research-reopens"]} glossary={doc.glossary} />);
  const link = screen.getByRole("link", { name: "BLBD" });
  expect(link).toHaveAttribute(
    "href",
    `${REPO_URL}/blob/main/research/BLBD-2026-07-28.md`,
  );
});

test("an event-trigger row's ticker also links to its thesis doc", () => {
  render(<ResearchReopens sec={doc.sections["research-reopens"]} glossary={doc.glossary} />);
  const link = screen.getByRole("link", { name: "DASH" });
  expect(link).toHaveAttribute(
    "href",
    `${REPO_URL}/blob/main/research/DASH-2026-07-28.md`,
  );
});

test("a row with no resolvable thesis path renders plain text instead of a link", () => {
  const sec = {
    ...doc.sections["research-reopens"],
    rows: [
      {
        ticker: "XYZ",
        verdict: null,
        due: null,
        trigger: "malformed",
        thesis_date: "not-a-date",
        thesis_path: null,
      },
    ],
  };
  render(<ResearchReopens sec={sec} glossary={doc.glossary} />);
  expect(screen.getByText("XYZ")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "XYZ" })).not.toBeInTheDocument();
});

test("held-ticker checkpoints render above the table, with a 'today' label for when_days: 0", () => {
  render(<ResearchReopens sec={doc.sections["research-reopens"]} glossary={doc.glossary} />);
  expect(screen.getByText(/held position checkpoint/)).toBeInTheDocument();
  expect(screen.getByText(/\(today\)/)).toBeInTheDocument();
});

test("no checkpoint list renders when checkpoints is absent", () => {
  const sec = { ...doc.sections["research-reopens"], checkpoints: undefined };
  render(<ResearchReopens sec={sec} glossary={doc.glossary} />);
  expect(screen.queryByText(/held position checkpoint/)).not.toBeInTheDocument();
});
