import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { TraderScorecard } from "./TraderScorecard";

const doc = fixture as unknown as DashboardDoc;

test("renders the plain-text report verbatim inside a mono <pre>", () => {
  const { container } = render(
    <TraderScorecard sec={doc.sections["plan-004-scorecard"]} glossary={doc.glossary} />,
  );
  const pre = container.querySelector("pre.mono");
  expect(pre).not.toBeNull();
  expect(pre?.textContent).toBe((doc.sections["plan-004-scorecard"].text_lines ?? []).join("\n"));
  // Real header from scorer/scorecard.py's build_report: "=== Trader
  // Decision-Quality Scorecard — YYYY-MM ===".
  expect(screen.getByText(/Trader Decision-Quality Scorecard/)).toBeInTheDocument();
});
