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
  expect(screen.getAllByText(/SOUND/).length).toBeGreaterThan(0);
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

// ---- screen + thesis blocks (deep500-style: the number and the research
// opinion side by side, the thesis inline instead of a link-out) ----

const THESIS_MD = `# AAPL — Apple — 2026-06-15

## 1. Verdict and thesis

**Ownership call: PASS at $190.**

## 5. Falsifiers

| falsifier | status |
|---|---|
| services decel | not fired |
`;

function stubThesisFetch(status = 200, body = THESIS_MD) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: status === 200, status, text: async () => body }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("screen block shows the candidate row, on-list trend, and the research call together", () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  expect(screen.getByRole("heading", { name: /screen/i })).toBeInTheDocument();
  expect(screen.getByText("5.4%")).toBeInTheDocument(); // fcf yield
  expect(screen.getByText(/8 → 7/)).toBeInTheDocument(); // fScore entry → now
  expect(screen.getByText(/12d/)).toBeInTheDocument(); // days on list
  expect(screen.getByText("pass")).toBeInTheDocument(); // research call pill
});

test("screen block is absent for a ticker that is not on the candidates screen", () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="TSLA" />);
  expect(screen.queryByRole("heading", { name: /^screen$/i })).not.toBeInTheDocument();
});

test("thesis block fetches theses/<SYM>.md and renders markdown with GFM tables", async () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  expect(fetch).toHaveBeenCalledWith("./theses/AAPL.md");
  expect(await screen.findByRole("heading", { name: /1\. Verdict and thesis/ })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "services decel" })).toBeInTheDocument();
  expect(screen.getByText("Ownership call: PASS at $190.")).toBeInTheDocument();
});

test("thesis block offers a jump-list built from the ## headings", async () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  const nav = await screen.findByRole("navigation", { name: /thesis sections/i });
  expect(nav).toHaveTextContent("1. Verdict and thesis");
  expect(nav).toHaveTextContent("5. Falsifiers");
});

test("thesis block degrades when the file is missing", async () => {
  stubThesisFetch(404, "");
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  expect(await screen.findByText(/thesis file not published/i)).toBeInTheDocument();
  // the repo link still works as the fallback
  expect(screen.getAllByRole("link", { name: /thesis/i }).length).toBeGreaterThan(0);
});

test("thesis block is absent for a ticker with no thesis", () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="TSLA" />);
  expect(screen.queryByRole("heading", { name: /^thesis$/i })).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

// ---- About modals: the same AboutDialog convention as the main-page
// sections — one-sentence note on the card, the explainer behind the
// info icon as headed blocks. ----

test("every rendered block carries an About trigger", () => {
  stubThesisFetch();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  for (const name of [
    "Screen",
    "Score history",
    "Signal breakdown",
    "Research verdicts",
    "Thesis",
    "Journal fills",
    "Your position",
  ]) {
    expect(screen.getByRole("button", { name: `About ${name}` })).toBeInTheDocument();
  }
});

test("the Screen block's About modal explains the accruals sign and the research call", async () => {
  stubThesisFetch();
  const user = userEvent.setup();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  await user.click(screen.getByRole("button", { name: "About Screen" }));
  const dialog = screen.getByRole("dialog");
  expect(dialog).toHaveTextContent(/negative/i); // accruals sign convention
  expect(dialog).toHaveTextContent(/pass/i); // what a pass beside a quality row means
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("the Thesis block's About modal says the ownership call is graded, not the prose", async () => {
  stubThesisFetch();
  const user = userEvent.setup();
  render(<TickerDetail doc={doc} symbol="AAPL" />);
  await user.click(screen.getByRole("button", { name: "About Thesis" }));
  expect(screen.getByRole("dialog")).toHaveTextContent(/graded/i);
});
