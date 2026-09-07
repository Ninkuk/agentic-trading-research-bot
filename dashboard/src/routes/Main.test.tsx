import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import { KICKERS, type DashboardDoc, type Kicker } from "../types";
import { Main } from "./Main";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
  location.hash = "";
});

test("renders every hero bullet", () => {
  render(<Main doc={doc} />);
  for (const bullet of doc.hero.bullets) {
    expect(screen.getByText(bullet.text)).toBeInTheDocument();
  }
});

test("hero bullets link known tickers to their drill-down route", () => {
  const withFlag: DashboardDoc = {
    ...doc,
    hero: {
      bullets: [
        { text: "AAPL is flagged tonight and worth a look.", tone: "mid" },
      ],
    },
  };
  render(<Main doc={withFlag} />);
  // Scope to the hero: the scorecard below also links AAPL by design.
  const hero = within(document.querySelector(".hero") as HTMLElement);
  const link = hero.getByRole("link", { name: "AAPL" });
  expect(link).toHaveAttribute("href", "#/ticker/AAPL");
  // Words that merely look uppercase-ish but aren't exported tickers stay text.
  expect(hero.queryByRole("link", { name: "VIX" })).not.toBeInTheDocument();
});

function strandEl(slug: string): HTMLElement {
  return document.getElementById(slug) as HTMLElement;
}

test("renders every strand as a force-mounted section in order; all inactive on the Summary route", () => {
  render(<Main doc={doc} />);
  const strands = Array.from(document.querySelectorAll("section.strand")).map(
    (s) => s.id,
  );
  expect(strands).toEqual(
    KICKERS.map((k) => k.toLowerCase().replace(/\s+/g, "-")),
  );
  for (const s of strands)
    expect(strandEl(s)).toHaveAttribute("data-state", "inactive");
  expect(document.querySelector(".hero")).not.toBeNull();
});

test("a strand route activates that strand and hides the Summary", () => {
  location.hash = "#/signals";
  render(<Main doc={doc} />);
  expect(strandEl("signals")).toHaveAttribute("data-state", "active");
  expect(strandEl("macro")).toHaveAttribute("data-state", "inactive");
  expect(document.querySelector(".hero")).toBeNull();
});

test("an unknown strand slug falls back to the Summary", () => {
  location.hash = "#/nonsense";
  render(<Main doc={doc} />);
  expect(document.querySelector(".hero")).not.toBeNull();
  for (const s of document.querySelectorAll("section.strand")) {
    expect(s).toHaveAttribute("data-state", "inactive");
  }
});

test("a bare section anchor activates the strand holding it and scrolls the section into view", () => {
  const scrollIntoView = vi.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  location.hash = "#equity-curve";
  render(<Main doc={doc} />);
  expect(strandEl("track-record")).toHaveAttribute("data-state", "active");
  expect(scrollIntoView).toHaveBeenCalled();
  expect((scrollIntoView.mock.contexts[0] as HTMLElement).id).toBe(
    "equity-curve",
  );
});

// The fixture's Sources strand is mostly quiet (3 live cards), so the
// grouped layout needs a synthetic strand: nine live cards over three
// publishers plus one card with no publisher at all.
function groupedSourcesDoc(): DashboardDoc {
  const columns = [
    { key: "x", label: "X", numeric: false, direction: null, term: null },
  ];
  const rows = Array.from({ length: 8 }, (_, i) => ({ x: `r${i}` }));
  const others = Object.fromEntries(
    Object.entries(doc.sections).filter(([, sec]) => sec.kicker !== "Sources"),
  );
  const card = (title: string, source?: string) => ({
    title,
    kicker: "Sources" as const,
    source,
    columns,
    rows,
  });
  return {
    ...doc,
    sections: {
      ...others,
      "t-debt": card("Federal debt", "Treasury"),
      "f-rates": card("Funding markets", "NY Fed"),
      "s-rev": card("Restated financials", "SEC"),
      "t-auct": card("Auction demand", "Treasury"),
      "s-ftd": card("Fails spikes", "SEC"),
      "s-ins": card("Insider filings", "SEC"),
      "f-deal": card("Dealer positions", "NY Fed"),
      lone: card("Lone card"),
      "t-up": card("Upcoming auctions", "Treasury"),
    },
  };
}

test("a long multi-publisher strand groups its cards under headings, and a group anchor routes to it", () => {
  const scrollIntoView = vi.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  location.hash = "#sources-sec";
  render(<Main doc={groupedSourcesDoc()} />);
  expect(strandEl("sources")).toHaveAttribute("data-state", "active");
  expect((scrollIntoView.mock.contexts[0] as HTMLElement).id).toBe(
    "sources-sec",
  );
  const sources = within(strandEl("sources"));
  const nav = sources.getByRole("navigation", {
    name: "sections in this strand",
  });
  expect(
    Array.from(nav.querySelectorAll("a")).map((a) => a.textContent),
  ).toEqual(["Treasury", "NY Fed", "SEC", "Lone card"]);
  const group = sources.getByRole("group", { name: "SEC" });
  expect(within(group).getByRole("heading", { name: "SEC" })).toHaveAttribute(
    "id",
    "sources-sec",
  );
  for (const id of ["s-rev", "s-ftd", "s-ins"])
    expect(group.querySelector(`#${id}`)).not.toBeNull();
  // Treasury's third card sat last in exporter order; grouping pulls it up beside its siblings.
  const treasury = sources.getByRole("group", { name: "Treasury" });
  expect(
    Array.from(treasury.querySelectorAll("section")).map((s) => s.id),
  ).toEqual(["t-debt", "t-auct", "t-up"]);
  // A source-less card renders bare: one element with its id, no heading, its chip links straight to it.
  expect(document.querySelectorAll("#lone").length).toBe(1);
  expect(sources.queryByRole("group", { name: "Lone card" })).toBeNull();
  expect(sources.getByRole("link", { name: "Lone card" })).toHaveAttribute(
    "href",
    "#lone",
  );
});

test("shorter or single-publisher strands stay ungrouped: no headings, no chip row", () => {
  render(<Main doc={doc} />);
  for (const slug of ["macro", "signals", "sources"]) {
    expect(within(strandEl(slug)).queryByRole("navigation")).toBeNull();
    // Only publisher groups label themselves by a heading; toggle groups don't.
    expect(
      strandEl(slug).querySelector("[role=group][aria-labelledby]"),
    ).toBeNull();
  }
});

test("the Summary indexes every strand with a link into it", () => {
  render(<Main doc={doc} />);
  const index = within(document.querySelector(".strand-index") as HTMLElement);
  for (const label of KICKERS) {
    expect(
      index.getByRole("link", { name: new RegExp(`^${label}`) }),
    ).toHaveAttribute("href", `#/${label.toLowerCase().replace(/\s+/g, "-")}`);
  }
});

test("a section with a kicker matching no known strand still renders, in a trailing Other group", () => {
  const drifted: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "renamed-strand-section": {
        title: "Renamed Strand Section",
        // Simulates a Python-side kicker rename/typo the frontend hasn't
        // caught up to — TypeScript can't catch this (it's live JSON), so
        // this is the runtime case the "Other" fallback exists for.
        kicker: "Vibes" as unknown as Kicker,
        columns: [
          { key: "x", label: "X", numeric: false, direction: null, term: null },
        ],
        rows: [{ x: "hello" }],
      },
    },
  };
  render(<Main doc={drifted} />);
  expect(strandEl("other")).toHaveClass("strand");
  // Strands are force-mounted (hidden when inactive), so the drifted
  // section's content is in the DOM even though Other isn't the route.
  expect(screen.getByText("Renamed Strand Section")).toBeInTheDocument();
  expect(screen.getByText("hello")).toBeInTheDocument();
});

test("no Other strand renders when every section's kicker matches a known strand", () => {
  render(<Main doc={doc} />);
  expect(document.getElementById("other")).toBeNull();
});

test("a section with an error shows the unavailable note instead of crashing", () => {
  const errored = {
    ...doc,
    sections: {
      ...doc.sections,
      candidates: {
        ...doc.sections.candidates,
        columns: undefined,
        rows: undefined,
        error: "unavailable (stocks.db: OperationalError)",
      },
    },
  } as DashboardDoc;
  render(<Main doc={errored} />);
  expect(screen.getByText(/unavailable \(stocks\.db/i)).toBeInTheDocument();
});

test("scorecard symbols link to the ticker route", () => {
  render(<Main doc={doc} />);
  // There is deliberately no masthead search box — symbol links are the
  // way into the drill-down.
  // AAPL appears on the scorecard AND the candidates list; both link in.
  const links = screen.getAllByRole("link", { name: "AAPL" });
  expect(links.length).toBeGreaterThan(0);
  for (const l of links) expect(l).toHaveAttribute("href", "#/ticker/AAPL");
});

test("an unregistered section id falls back to the generic DataTable renderer", () => {
  // Every real section id has a dedicated registered component, so
  // this constructs a synthetic id no registry entry can ever claim — it
  // must still render its columns and rows via GenericSection, not go blank.
  const withUnregistered: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "totally-new-section": {
        title: "Totally New Section",
        kicker: "Signals",
        columns: [
          {
            key: "symbol",
            label: "Symbol",
            numeric: false,
            direction: null,
            term: null,
          },
        ],
        rows: [{ symbol: "ZZZZ" }],
      },
    },
  };
  render(<Main doc={withUnregistered} />);
  const region = within(
    document.getElementById("totally-new-section") as HTMLElement,
  );
  expect(
    region.getByRole("columnheader", { name: /symbol/i }),
  ).toBeInTheDocument();
  expect(region.getByText("ZZZZ")).toBeInTheDocument();
});

test("generic fallback sections with duplicate titles keep independent page state (keyed by id, not title)", async () => {
  const columns = [
    { key: "x", label: "X", numeric: false, direction: null, term: null },
  ];
  const manyRows = Array.from({ length: 10 }, (_, i) => ({ x: `row-${i}` }));
  const dup: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "dup-one": {
        title: "Duplicate Title",
        kicker: "Research",
        columns,
        rows: manyRows,
      },
      "dup-two": {
        title: "Duplicate Title",
        kicker: "Research",
        columns,
        rows: manyRows,
      },
    },
  };
  render(<Main doc={dup} />);
  const nextButtons = screen.getAllByRole("button", { name: /next page/i });
  expect(nextButtons).toHaveLength(2); // both start on page one, independently
  await userEvent.click(nextButtons[0]);
  // Paging one duplicate-titled section must not touch the other — the page
  // is per-table component state, but the sort prefs are still
  // storageKey-scoped, so duplicate titles must not share a key.
  expect(screen.getAllByText("9–10 of 10")).toHaveLength(1);
  expect(screen.getAllByText("1–8 of 10")).toHaveLength(1);
});

test("a pinned ticker (shared pins pref) stays first in the scorecard despite an active score sort", () => {
  localStorage.setItem("atrb:pins", JSON.stringify(["MSFT"]));
  localStorage.setItem(
    "atrb:scorecard",
    JSON.stringify({
      sortKey: "score_sum",
      sortDir: "desc",
      expanded: false,
      hiddenCols: [],
    }),
  );
  render(<Main doc={doc} />);
  const scorecard = within(document.getElementById("scorecard") as HTMLElement);
  const rows = scorecard.getAllByRole("row").slice(1); // drop the header row
  // Sorted desc by score_sum without pinning would put AAPL (4) first —
  // MSFT (1) must lead anyway because it's pinned.
  expect(within(rows[0]).getByRole("link")).toHaveTextContent("MSFT");
});

test("regime section renders its tiles and drivers table", () => {
  render(<Main doc={doc} />);
  // The regime verdict shows twice by design: once compact in the KPI row,
  // once again in the Macro strand's Regime section header.
  expect(
    screen.getAllByText("Risk-on, 3rd night").length,
  ).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("VIX level")).toBeInTheDocument();
});

test("empty sections collapse into the strand's Quiet tonight list, ids intact", () => {
  const withQuiet: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "nothing-tonight": {
        title: "Nothing Tonight",
        kicker: "Ops",
        columns: [
          { key: "x", label: "X", numeric: false, direction: null, term: null },
        ],
        rows: [],
        empty: "no rows this run",
      },
    },
  };
  render(<Main doc={withQuiet} />);
  const row = document.getElementById("nothing-tonight") as HTMLElement;
  expect(row.tagName).toBe("LI");
  expect(within(row).getByText("no rows this run")).toBeInTheDocument();
  expect(row.closest(".quiet-list")).not.toBeNull();
});

test("short row-only sections share a two-up grid; long ones stay full width", () => {
  const columns = [
    { key: "x", label: "X", numeric: false, direction: null, term: null },
  ];
  const shortRows = [{ x: "a" }, { x: "b" }];
  const longRows = Array.from({ length: 12 }, (_, i) => ({ x: `r${i}` }));
  const grid: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "short-a": { title: "Short A", kicker: "Ops", columns, rows: shortRows },
      "short-b": { title: "Short B", kicker: "Ops", columns, rows: shortRows },
      "long-c": { title: "Long C", kicker: "Ops", columns, rows: longRows },
    },
  };
  render(<Main doc={grid} />);
  const a = document.getElementById("short-a") as HTMLElement;
  const c = document.getElementById("long-c") as HTMLElement;
  expect(a.parentElement?.className).toContain("md:grid-cols-2");
  // Paired cards stretch to the same height: the grid pushes h-full down
  // through the section wrapper to the Card.
  expect(a.parentElement?.className).toContain("[&>section]:h-full");
  expect(a.parentElement?.className).toContain("[&>section]:min-w-0");
  expect(a.parentElement?.className).toContain("[&>section>div]:h-full");
  expect(a.parentElement).toBe(
    document.getElementById("short-b")?.parentElement,
  );
  expect(c.parentElement?.className).not.toContain("md:grid-cols-2");
});

test("a lone short section renders full width, not half a grid", () => {
  const columns = [
    { key: "x", label: "X", numeric: false, direction: null, term: null },
  ];
  const longRows = Array.from({ length: 12 }, (_, i) => ({ x: `r${i}` }));
  const lone: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      // The fixture's Ops strand carries short cards (pending, basis-breaks);
      // lengthen them so lone-short is the strand's only short section.
      pending: { ...doc.sections["pending"], rows: longRows },
      "basis-breaks": { ...doc.sections["basis-breaks"], rows: longRows },
      "lone-short": {
        title: "Lone Short",
        kicker: "Ops",
        columns,
        rows: [{ x: "a" }],
      },
    },
  };
  render(<Main doc={lone} />);
  const a = document.getElementById("lone-short") as HTMLElement;
  expect(a.parentElement?.className).not.toContain("md:grid-cols-2");
});
