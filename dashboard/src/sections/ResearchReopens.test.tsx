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

const SUMMARY_ROWS = [
  { ticker: "HMY", held: false, verdict: "UNPROVEN", due: "2026-08-27", trigger: "fy26-results", thesis_date: "2026-07-30", thesis_path: null },
  { ticker: "INTU", held: true, verdict: "SOUND", due: "2026-09-02", trigger: "intu-investor-day", thesis_date: "2026-08-25", thesis_path: null },
  { ticker: "CPRT", held: false, verdict: "FLAWED", due: "2026-09-26", trigger: "q4-print", thesis_date: "2026-07-26", thesis_path: null },
  { ticker: "GFI", held: true, verdict: "UNPROVEN", due: null, trigger: "tarkwa-renewal", thesis_date: "2026-07-01", thesis_path: null },
];

test("KPI tiles count open theses, held, and due within 7 days of the injected today", () => {
  const sec = { ...doc.sections["research-reopens"], rows: SUMMARY_ROWS, checkpoints: undefined };
  render(<ResearchReopens sec={sec} glossary={doc.glossary} today="2026-08-27" />);
  expect(screen.getByText("open theses").previousSibling).toHaveTextContent("4");
  expect(screen.getByText("held").previousSibling).toHaveTextContent("2");
  // HMY (day 0) and INTU (day 6); CPRT is day 30, GFI undated
  expect(screen.getByText("due within 7 days").previousSibling).toHaveTextContent("2");
});
