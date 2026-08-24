import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { ResearchReopens } from "./ResearchReopens";

const doc = fixture as unknown as DashboardDoc;

test("links a dated row's ticker to its page, where the thesis renders inline", () => {
  render(<ResearchReopens sec={doc.sections["research-reopens"]} glossary={doc.glossary} />);
  const link = screen.getByRole("link", { name: "BLBD" });
  expect(link).toHaveAttribute(
    "href",
    "#/ticker/BLBD",
  );
});

test("an event-trigger row's ticker also links to its page", () => {
  // Built inline rather than pulled from the fixture: link rendering keys
  // off thesis_path only (see renderReopensCell), never `due` — an
  // event-shaped row (due: null) must link exactly like a dated one.
  const sec = {
    ...doc.sections["research-reopens"],
    rows: [
      {
        ticker: "GFI",
        verdict: "UNPROVEN",
        due: null,
        trigger: "tarkwa-renewal",
        thesis_date: "2026-07-01",
        thesis_path: "research/GFI-2026-07-01.md",
      },
    ],
  };
  render(<ResearchReopens sec={sec} glossary={doc.glossary} />);
  const link = screen.getByRole("link", { name: "GFI" });
  expect(link).toHaveAttribute(
    "href",
    "#/ticker/GFI",
  );
});

test("a row with no resolvable thesis path still links to its page", () => {
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
  expect(screen.getByRole("link", { name: "XYZ" })).toHaveAttribute("href", "#/ticker/XYZ");
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

test("every checkpoint's ticker has a fixture row with a non-null due", () => {
  // Pins what the exporter actually guarantees: `checkpoints` is built only
  // from dated (due != null) rows (data.py's `_research_reopens`), so a
  // checkpoint whose ticker's row has `due: null` is an impossible shape
  // the exporter cannot emit.
  const sec = doc.sections["research-reopens"];
  const rowsByTicker = new Map((sec.rows ?? []).map((r) => [r.ticker, r]));
  for (const c of sec.checkpoints ?? []) {
    expect(rowsByTicker.get(c.ticker)?.due).not.toBeNull();
  }
});
