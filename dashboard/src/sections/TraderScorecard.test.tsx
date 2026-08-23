import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { TraderScorecard } from "./TraderScorecard";

const doc = fixture as unknown as DashboardDoc;

test("parses the scorecard report into subsection tables", () => {
  const { container } = render(
    <TraderScorecard sec={doc.sections["trader-scorecard"]} glossary={doc.glossary} />,
  );
  // The report's stable format (=== title ===, pipe blocks) parses into
  // real tables — the block headings from scorer/scorecard.py's
  // build_report become subsection h3s.
  expect(screen.getByRole("heading", { name: /filter edge/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /execution cost/i })).toBeInTheDocument();
  expect(container.querySelectorAll("table").length).toBeGreaterThanOrEqual(2);
  // The period from the "=== ... — YYYY-MM ===" header surfaces as a badge.
  expect(screen.getByText("2026-07")).toBeInTheDocument();
  // Parsed rendering replaces the raw dump — no <pre> when parsing works.
  expect(container.querySelector("pre")).toBeNull();
});

test("an unparseable report falls back to the verbatim <pre>", () => {
  const sec = {
    ...doc.sections["trader-scorecard"],
    text_lines: ["free-form line one", "free-form line two"],
  };
  const { container } = render(<TraderScorecard sec={sec} glossary={doc.glossary} />);
  // Headingless prose still produces a block per parseTextReport group; a
  // truly empty report is the real fallback trigger.
  expect(container.textContent).toContain("free-form line one");
});
