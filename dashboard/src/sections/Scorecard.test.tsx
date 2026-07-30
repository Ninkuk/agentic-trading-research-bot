import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Scorecard } from "./Scorecard";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
});

test("renders the signed score, the symbol link, and a flagged row's brass edge", () => {
  render(<Scorecard sec={doc.sections.scorecard} glossary={doc.glossary} />);
  expect(screen.getByText("+4")).toBeInTheDocument(); // AAPL's score_sum via ScoreBar
  const aaplLink = screen.getByRole("link", { name: "AAPL" });
  expect(aaplLink).toHaveAttribute("href", "#/ticker/AAPL");
  expect(aaplLink).toHaveClass("sym");
  // AAPL is flagged -> its <tr> carries the "flag" class the static page's
  // CSS keys the ★ + brass left-edge treatment off (tr.flag / tr.flag .sym::after).
  expect(aaplLink.closest("tr")).toHaveClass("flag");
  // TSLA is not flagged.
  const tslaLink = screen.getByRole("link", { name: "TSLA" });
  expect(tslaLink.closest("tr")).not.toHaveClass("flag");
});

test("typing in the ticker filter narrows rows to the matching symbol, case-insensitively", async () => {
  render(<Scorecard sec={doc.sections.scorecard} glossary={doc.glossary} />);
  const input = screen.getByRole("searchbox", { name: /filter tickers/i });
  await userEvent.type(input, "de");
  expect(screen.getByRole("link", { name: "DECK" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "AAPL" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "TSLA" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "MSFT" })).not.toBeInTheDocument();
});

test("the filter input persists across remounts via usePrefs", async () => {
  const { unmount } = render(<Scorecard sec={doc.sections.scorecard} glossary={doc.glossary} />);
  const input = screen.getByRole("searchbox", { name: /filter tickers/i });
  await userEvent.type(input, "de");
  unmount();
  render(<Scorecard sec={doc.sections.scorecard} glossary={doc.glossary} />);
  expect(screen.getByRole("searchbox", { name: /filter tickers/i })).toHaveValue("DE");
  expect(screen.getByRole("link", { name: "DECK" })).toBeInTheDocument();
});
