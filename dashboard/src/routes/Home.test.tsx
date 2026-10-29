import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import type { DashboardDoc, Section } from "../types";
import { bestCall, lastNight, researchCounts, stocksBought } from "../home/homeFacts";
import { suggestionHref } from "../home/suggest";
import { Home } from "./Home";

const doc = fixture as unknown as DashboardDoc;

// The thesis one-liner is fetched from the published file; here no file is
// published, so the research chapter shows its plain fallback.
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function without(...ids: string[]): DashboardDoc {
  const sections = { ...doc.sections };
  for (const id of ids) delete sections[id];
  return { ...doc, sections };
}

const graded: Record<string, Section> = {
  "research-filter": {
    rows: [
      { verdict: "buy", horizon: 21, n: 45, hit_rate: 0.556 },
      { verdict: "pass", horizon: 21, n: 234, hit_rate: 0.581 },
    ],
  },
  "research-calibration": {
    verdict: { text: "Confidence matched results: said 46%, won 44%", tone: "mid" },
    tiles: [{ label: "Forecast error", value: "0.24", band: "guessing the base rate scores 0.25", tone: "on" }],
    rows: [{ horizon: 21, p_bin: "40–50%", n: 93, n_dates: 30 }],
  },
};

test("the beats render in order: headline, the night's story, scorecard, where next", () => {
  render(<Home doc={doc} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "A research desk that grades its own work.",
  );
  const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(headings).toEqual([
    "What happens every evening.",
    "Has it been right?",
    "Where to go from here.",
    "Suggest a stock.",
  ]);
});

test("in-page links scroll without touching the hash (a bare #id would route to a strand)", async () => {
  const scrolled: string[] = [];
  Element.prototype.scrollIntoView = function (this: Element) {
    scrolled.push(this.id);
  };
  render(<Home doc={doc} />);
  for (const name of ["Watch one night", "See the scorecard"]) {
    const [link] = screen.getAllByRole("link", { name });
    expect(link).toHaveAttribute("href", "#/");
    await userEvent.click(link);
  }
  expect(scrolled).toEqual(["story", "scorecard"]);
  expect(location.hash).toBe("");
  // Cross-route anchors stay real hashes: the grading links land on strand sections.
  cleanup();
  render(<Home doc={{ ...doc, sections: { ...doc.sections, ...graded } }} />);
  expect(screen.getAllByRole("link", { name: "See the grading" })[0]).toHaveAttribute("href", "#research-filter");
});

test("a suggested ticker becomes a prefilled GitHub issue link, nothing else", async () => {
  render(<Home doc={doc} />);
  const box = screen.getByLabelText("Ticker");
  // Nothing typed: no link, the button is inert.
  expect(screen.queryByRole("link", { name: "Suggest it" })).not.toBeInTheDocument();
  // Digits, spaces and symbols never land in the box; letters uppercase as typed.
  await userEvent.type(box, "br1k. b$");
  expect(box).toHaveValue("BRK.B");
  const link = screen.getByRole("link", { name: "Suggest it" });
  expect(link).toHaveAttribute("target", "_blank");
  expect(link.getAttribute("href")).toBe(suggestionHref("BRK.B"));
  expect(link.getAttribute("href")).toContain("issues/new?template=research-request.yml&title=Research%3A+BRK.B");
  await userEvent.clear(box);
  await userEvent.type(box, "toolongname");
  expect(box).toHaveValue("TOOLONGN");
  expect(screen.queryByRole("link", { name: "Suggest it" })).not.toBeInTheDocument();
  expect(box).toHaveAttribute("aria-invalid", "true");
});

test("the story has one chapter per step of the run, with last night's output", () => {
  render(<Home doc={doc} />);
  // The Timeline renders each title twice (sticky desktop column, inline on
  // phones); the chapter order is what matters.
  const titles = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
  const seen = titles.filter((t, i) => titles.indexOf(t) === i);
  expect(seen).toEqual([
    "Read",
    "Gauge the market",
    "Grade the old ones",
    "Research a name",
    "Attack the thesis",
    "A person decides",
  ]);
  const night = lastNight(doc);
  expect(screen.getByText(`${night.regime!}.`, { exact: false })).toBeInTheDocument();
  expect(screen.getByText(`last night: ${night.thesis!.ticker} · ${night.thesis!.call}`)).toBeInTheDocument();
  // The rebuilt log lines stay inside the terminal; no chapter quotes one as a chip.
  expect(screen.queryByText(/composite snapshot|scorer snapshot|done: \d+ ok/)).not.toBeInTheDocument();
  // The terminal replays the read jobs' real commands (typed once in view;
  // jsdom never scrolls, so the title bar is what renders).
  expect(screen.getByText("~/agentic-trading-research-bot — last night")).toBeInTheDocument();
});

test("the counters come from the research and timeline sections", () => {
  render(<Home doc={doc} />);
  expect(screen.getByText("Running every night")).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/snapshot #|Phoenix/);
  // jsdom never scrolls the row into view, so the tickers hold at zero; the
  // labels and the order are what this checks, the arithmetic is homeFacts'.
  const labels = screen.getAllByRole("term").map((t) => t.textContent);
  expect(labels).toEqual(["stocks researched", "stocks bought", "nights running", "up overall"]);
  expect(researchCounts(doc)!.theses).toBeGreaterThan(0);
  expect(stocksBought(doc)).toBeGreaterThan(0);
});

test("the best graded buy call is the featured thesis, in the story and in where-next", () => {
  render(<Home doc={doc} />);
  const best = bestCall(doc)!;
  const links = screen.getAllByRole("link", { name: /best call so far|whole thesis/i });
  expect(links.length).toBe(2);
  for (const link of links) expect(link).toHaveAttribute("href", `#/ticker/${best.symbol}`);
  // The line appears in the research chapter (no thesis file published
  // here, so the plain fallback) and again in where-next.
  expect(screen.getAllByText(/\+14\.8 points vs SPY over 21 trading days, called Jul 28/).length).toBe(2);
});

test("the thesis sentence shows only when the published thesis is the graded call's", async () => {
  const best = bestCall(doc)!;
  const md = "# DASH\n\n> [!IMPORTANT]\n> **In one sentence:** DoorDash earns more than its price assumes, so buy.\n";
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, text: async () => md }));
  const thesis = { path: "research/DASH.md", date: best.verdict_date, verdict: "SOUND", reopen: null, file: "theses/DASH.md" };
  const withThesis: DashboardDoc = {
    ...doc,
    tickers: { ...doc.tickers, [best.symbol]: { ...doc.tickers[best.symbol], thesis } },
  };
  render(<Home doc={withThesis} />);
  expect(await screen.findByLabelText("DoorDash earns more than its price assumes, so buy.")).toBeInTheDocument();

  // A newer thesis for the same ticker is a different call: no sentence, the plain line instead.
  cleanup();
  const newer: DashboardDoc = {
    ...withThesis,
    tickers: { ...withThesis.tickers, [best.symbol]: { ...withThesis.tickers[best.symbol], thesis: { ...thesis, date: "2026-09-01" } } },
  };
  render(<Home doc={newer} />);
  expect(screen.queryByLabelText(/DoorDash earns/)).not.toBeInTheDocument();
  expect(screen.getAllByText(/\+14\.8 points vs SPY/).length).toBe(2);
});

test("without a graded buy there is no featured thesis anywhere", () => {
  const sec = doc.sections["research-verdict-outcomes"];
  render(<Home doc={{ ...doc, sections: { ...doc.sections, "research-verdict-outcomes": { ...sec, best_call: null } } }} />);
  expect(screen.queryByRole("link", { name: /best call so far|whole thesis/i })).not.toBeInTheDocument();
});

test("the scorecard shows the exporter's curve figures and the grade cards when graded", () => {
  render(<Home doc={{ ...doc, sections: { ...doc.sections, ...graded } }} />);
  const sec = doc.sections["equity-curve"];
  expect(screen.getByText("The picks").parentElement).toHaveTextContent(String(sec.tiles![0].value));
  expect(screen.getByText(sec.verdict!.text)).toBeInTheDocument();
  expect(screen.getByText("Buy calls right").previousSibling).toHaveTextContent("56%");
  expect(screen.getByText("Confidence vs results").previousSibling).toHaveTextContent("said 46%, won 44%");
  expect(screen.getByText("Market signals still unproven").previousSibling).toHaveTextContent("1 of 1");
  // The grade chapter turns the calibration verdict into the reveal card.
  expect(screen.getByText("It said it would win 46% of the time.")).toBeInTheDocument();
  expect(screen.getByText("It won 44%.")).toBeInTheDocument();
});

test("each grade degrades alone; with nothing graded the scorecard says so", () => {
  render(<Home doc={doc} />);
  expect(screen.queryByText("Buy calls right")).not.toBeInTheDocument();
  expect(screen.queryByText("Confidence vs results")).not.toBeInTheDocument();
  expect(screen.getByText("Market signals still unproven")).toBeInTheDocument();
  expect(screen.getByText("nothing graded yet")).toBeInTheDocument();
});

test("with no graded section at all the scorecard shows its empty state", () => {
  render(<Home doc={without("equity-curve", "research-filter", "research-calibration", "signal-recommendations")} />);
  expect(screen.getByText(/nothing is graded yet/i)).toBeInTheDocument();
});

test("never addresses the reader as 'you', and never prices positions", () => {
  render(<Home doc={{ ...doc, sections: { ...doc.sections, ...graded } }} />);
  const text = document.body.textContent ?? "";
  expect(text).not.toMatch(/\byour?\b/i);
  expect(text).not.toMatch(/\d+ positions/);
  expect(text).not.toMatch(/\$\d{1,3}(,\d{3})+/);
});

test("a document with no sections still renders the front door", () => {
  render(<Home doc={{ ...doc, sections: {} }} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("grades its own work");
  expect(screen.getByRole("link", { name: /every researched name/i })).toHaveAttribute("href", "#/research");
  expect(screen.queryByRole("link", { name: /best call so far/i })).not.toBeInTheDocument();
  const story = within(document.getElementById("story") as HTMLElement);
  expect(story.getByText(/No mood call tonight/)).toBeInTheDocument();
});
