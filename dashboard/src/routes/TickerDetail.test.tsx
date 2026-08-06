import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import { tokens } from "../theme";
import type { DashboardDoc } from "../types";
import { TickerDetail } from "./TickerDetail";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
});

test("renders all four blocks for a fixture ticker with signals, verdicts, fills, and a position", () => {
  const { container } = render(<TickerDetail doc={doc} symbol="AAPL" />);

  expect(screen.getByRole("heading", { name: "AAPL" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /back/i })).toHaveAttribute("href", "#/");

  // score-history chart
  expect(container.querySelector(".score-history-line path")).toBeInTheDocument();

  // signal breakdown
  expect(screen.getByRole("columnheader", { name: /signal/i })).toBeInTheDocument();
  expect(screen.getByText("SI spike")).toBeInTheDocument();
  expect(screen.getByText("RSI oversold")).toBeInTheDocument();

  // research verdicts
  expect(screen.getByText(/SOUND/)).toBeInTheDocument();
  const thesisLink = screen.getByRole("link", { name: "thesis" });
  expect(thesisLink).toHaveAttribute(
    "href",
    "https://github.com/Ninkuk/agentic-trading-research-bot/blob/main/research/AAPL-2026-06-15.md",
  );

  // journal fills + position card
  expect(screen.getByText("194.32")).toBeInTheDocument(); // fill price
  expect(screen.getByText("$1,980.50")).toBeInTheDocument(); // market value
  expect(screen.getByText("0.50%")).toBeInTheDocument(); // heat pct (2 dp, matching the advisor tables)
});

test("each block degrades independently: TSLA has no research verdicts", () => {
  render(<TickerDetail doc={doc} symbol="TSLA" />);
  expect(screen.getByRole("heading", { name: "TSLA" })).toBeInTheDocument();
  expect(screen.getByText(/no research verdicts yet/i)).toBeInTheDocument();
  // signals and fills still render
  expect(screen.getByText("SI spike")).toBeInTheDocument();
});

test("score-history dots diverge by sign: zero is neutral, negative is down-colored", () => {
  const { container } = render(<TickerDetail doc={doc} symbol="TSLA" />);
  const dots = container.querySelectorAll(".score-dot");
  expect(dots.length).toBe(3); // 2026-07-27: 0, -07-28: -1, -07-29: -2
  expect(dots[0]).toHaveAttribute("fill", tokens.hold);
  expect(dots[1]).toHaveAttribute("fill", tokens.down);
  expect(dots[2]).toHaveAttribute("fill", tokens.down);
});

test("an unknown symbol shows an honest no-detail message, but the header (and pin) still renders", () => {
  render(<TickerDetail doc={doc} symbol="ZZZZ" />);
  expect(screen.getByRole("heading", { name: "ZZZZ" })).toBeInTheDocument();
  expect(
    screen.getByText(/no detail exported for ZZZZ; it was not in tonight's scorecard, holdings, or journal\./i),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /pin/i })).toBeInTheDocument();
});

test("pin toggle persists across remount via the shared pins pref", async () => {
  const { unmount } = render(<TickerDetail doc={doc} symbol="AAPL" />);
  const pinButton = screen.getByRole("button", { name: "☆ pin to top" });
  await userEvent.click(pinButton);
  expect(screen.getByRole("button", { name: "★ pinned to top" })).toBeInTheDocument();
  unmount();

  render(<TickerDetail doc={doc} symbol="AAPL" />);
  expect(screen.getByRole("button", { name: "★ pinned to top" })).toBeInTheDocument();
  expect(localStorage.getItem("atrb:pins")).toBe('["AAPL"]');
});

test("pinning one symbol does not pin another", async () => {
  const { unmount } = render(<TickerDetail doc={doc} symbol="AAPL" />);
  await userEvent.click(screen.getByRole("button", { name: "☆ pin to top" }));
  unmount();

  render(<TickerDetail doc={doc} symbol="TSLA" />);
  expect(screen.getByRole("button", { name: "☆ pin to top" })).toBeInTheDocument();
  expect(localStorage.getItem("atrb:pins")).toBe('["AAPL"]');
});
