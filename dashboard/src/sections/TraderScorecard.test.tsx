import { fireEvent, render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { TraderScorecard } from "./TraderScorecard";

const doc = fixture as unknown as DashboardDoc;

const LIVE_LINES = [
  "=== Trader Decision-Quality Scorecard — 2026-08 ===",
  "",
  "Filter edge (acted vs passed, by horizon)",
  "  horizon | response         | n  | avg_dir_excess | avg_fwd_return",
  "        5 | passed_inferred  | 62 | 0.0390         | 0.0327",
  "       10 | passed_inferred  | 47 | 0.1070         | 0.1455",
  "",
  "Execution cost (acted decisions, by horizon)",
  "  horizon | n  | avg_entry_slippage | avg_fill_lag_days",
  "        5 |  7 | -1.40%             | 1.00",
  "",
  "Alignment (acted decisions, by horizon)",
  "  horizon | agreed | contrarian | no opinion",
  "        5 |      2 |          5 |          0",
  "",
  "Portfolio vs SPY and cash (time-weighted)",
  "  window     | portfolio TWR | SPY      | excess   | cash (DFF)",
  "  inception  |         3.01% |    1.62% |    1.39% | 0.50%",
];

test("headline tiles lead and the sub-tables sit behind a closed Details toggle", () => {
  const sec = { ...doc.sections["trader-scorecard"], text_lines: LIVE_LINES };
  const { container } = render(<TraderScorecard sec={sec} glossary={doc.glossary} />);
  expect(screen.getByText("3.01%")).toHaveClass("tag-on");
  expect(screen.getByText("+1.39%")).toBeInTheDocument();
  expect(screen.getByText("+10.7%")).toBeInTheDocument();
  expect(screen.getByText("best pass edge · 10d · passed_inferred")).toBeInTheDocument();
  expect(screen.getByText("-1.40%")).toBeInTheDocument();
  expect(screen.getByText("2 / 5")).toBeInTheDocument();
  // Closed by default: no sub-tables until Details is opened.
  expect(container.querySelectorAll("table")).toHaveLength(0);
  const btn = screen.getByRole("button", { name: /details/i });
  expect(btn).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(btn);
  expect(btn).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("heading", { name: /filter edge/i })).toBeInTheDocument();
  expect(container.querySelectorAll("table").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("2026-08")).toBeInTheDocument();
  fireEvent.click(btn);
  expect(container.querySelectorAll("table")).toHaveLength(0);
});

test("fixture report still parses into subsection tables behind the toggle", () => {
  const { container } = render(
    <TraderScorecard sec={doc.sections["trader-scorecard"]} glossary={doc.glossary} />,
  );
  fireEvent.click(screen.getByRole("button", { name: /details/i }));
  expect(screen.getByRole("heading", { name: /execution cost/i })).toBeInTheDocument();
  expect(container.querySelector("pre")).toBeNull();
});

test("a report with no headline numbers renders the plain TextReport, no toggle", () => {
  const sec = {
    ...doc.sections["trader-scorecard"],
    text_lines: ["free-form line one", "free-form line two"],
  };
  const { container } = render(<TraderScorecard sec={sec} glossary={doc.glossary} />);
  expect(container.textContent).toContain("free-form line one");
  expect(screen.queryByRole("button", { name: /details/i })).toBeNull();
});
