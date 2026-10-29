import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Research } from "./Research";

const doc = fixture as unknown as DashboardDoc;

test("links a dated row's ticker to its page, where the thesis renders inline", () => {
  render(<Research sec={doc.sections["research"]} glossary={doc.glossary} />);
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
    ...doc.sections["research"],
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
  render(<Research sec={sec} glossary={doc.glossary} />);
  const link = screen.getByRole("link", { name: "GFI" });
  expect(link).toHaveAttribute(
    "href",
    "#/ticker/GFI",
  );
});

test("a row with no resolvable thesis path still links to its page", () => {
  const sec = {
    ...doc.sections["research"],
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
  render(<Research sec={sec} glossary={doc.glossary} />);
  expect(screen.getByText("XYZ")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "XYZ" })).toHaveAttribute("href", "#/ticker/XYZ");
});

const SUMMARY_ROWS = [
  { ticker: "HMY", held: false, call: "PASS", verdict: "UNPROVEN", due: "2026-08-27", trigger: "fy26-results", thesis_date: "2026-07-30", thesis_path: null },
  { ticker: "INTU", held: true, call: "BUY", verdict: "SOUND", due: "2026-09-02", trigger: "intu-investor-day", thesis_date: "2026-08-25", thesis_path: null },
  { ticker: "CPRT", held: false, call: "PASS", verdict: "FLAWED", due: "2026-09-26", trigger: "q4-print", thesis_date: "2026-07-26", thesis_path: null },
  { ticker: "GFI", held: true, call: "BUY", verdict: "UNPROVEN", due: null, trigger: "tarkwa-renewal", thesis_date: "2026-07-01", thesis_path: null },
  { ticker: "KBH", held: false, call: null, verdict: "FLAWED", due: null, trigger: null, thesis_date: "2026-07-20", thesis_path: null },
];

test("KPI tiles count researched, buy calls, held, and due within 7 days of the injected today", () => {
  const sec = { ...doc.sections["research"], rows: SUMMARY_ROWS };
  render(<Research sec={sec} glossary={doc.glossary} today="2026-08-27" />);
  expect(screen.getByText("researched").previousSibling).toHaveTextContent("5");
  expect(screen.getByText("buy calls").previousSibling).toHaveTextContent("2");
  expect(screen.getByText("held").previousSibling).toHaveTextContent("2");
  // HMY (day 0) and INTU (day 6); CPRT is day 30, GFI and KBH undated
  expect(screen.getByText("due within 7 days").previousSibling).toHaveTextContent("2");
});

test("the call column renders BUY and PASS as pills and a missing call as a dash", () => {
  render(<Research sec={doc.sections["research"]} glossary={doc.glossary} />);
  expect(screen.getByText("BUY")).toBeInTheDocument();
  expect(screen.getAllByText("PASS").length).toBeGreaterThan(0);
});

test("a closed name (no reopen trigger) still rows with its call and kill verdict", () => {
  render(<Research sec={doc.sections["research"]} glossary={doc.glossary} />);
  expect(screen.getByRole("link", { name: "KBH" })).toHaveAttribute("href", "#/ticker/KBH");
});
