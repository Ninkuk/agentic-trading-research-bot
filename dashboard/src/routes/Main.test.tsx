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

test("renders all five strand tabs in order", () => {
  render(<Main doc={doc} />);
  const tabs = screen.getAllByRole("tab").map((t) => t.textContent);
  const indices = KICKERS.map((label) => tabs.indexOf(label));
  for (const idx of indices) expect(idx).toBeGreaterThanOrEqual(0);
  expect(indices).toEqual([...indices].sort((a, b) => a - b));
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
        columns: [{ key: "x", label: "X", numeric: false, direction: null, term: null }],
        rows: [{ x: "hello" }],
      },
    },
  };
  render(<Main doc={drifted} />);
  expect(screen.getByRole("tab", { name: "Other" })).toBeInTheDocument();
  // Tab contents are force-mounted (hidden when inactive), so the drifted
  // section's content is in the DOM even though the Other tab isn't active.
  expect(screen.getByText("Renamed Strand Section")).toBeInTheDocument();
  expect(screen.getByText("hello")).toBeInTheDocument();
});

test("no Other tab renders when every section's kicker matches a known strand", () => {
  render(<Main doc={doc} />);
  expect(screen.queryByRole("tab", { name: "Other" })).not.toBeInTheDocument();
});

test("a section with an error shows the unavailable note instead of crashing", () => {
  render(<Main doc={doc} />);
  expect(screen.getByText(/unavailable \(stocks\.db/i)).toBeInTheDocument();
});

test("scorecard symbols link to the ticker route", () => {
  render(<Main doc={doc} />);
  // The masthead search box was removed 2026-07-30 — symbol links are the
  // way into the drill-down.
  expect(screen.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "#/ticker/AAPL");
});

test("an unregistered section id falls back to the generic DataTable renderer", () => {
  // Task 14 registered a dedicated component for every real section id, so
  // this constructs a synthetic id no registry entry can ever claim — it
  // must still render its columns and rows via GenericSection, not go blank.
  const withUnregistered: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "totally-new-section": {
        title: "Totally New Section",
        kicker: "Signals",
        columns: [{ key: "symbol", label: "Symbol", numeric: false, direction: null, term: null }],
        rows: [{ symbol: "ZZZZ" }],
      },
    },
  };
  render(<Main doc={withUnregistered} />);
  const region = within(document.getElementById("totally-new-section") as HTMLElement);
  expect(region.getByRole("columnheader", { name: /symbol/i })).toBeInTheDocument();
  expect(region.getByText("ZZZZ")).toBeInTheDocument();
});

test("generic fallback sections with duplicate titles keep independent persisted state (keyed by id, not title)", async () => {
  const columns = [{ key: "x", label: "X", numeric: false, direction: null, term: null }];
  const manyRows = Array.from({ length: 10 }, (_, i) => ({ x: `row-${i}` }));
  const dup: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      "dup-one": { title: "Duplicate Title", kicker: "Research", columns, rows: manyRows },
      "dup-two": { title: "Duplicate Title", kicker: "Research", columns, rows: manyRows },
    },
  };
  render(<Main doc={dup} />);
  const showAllButtons = screen.getAllByText(/show all 10/i);
  expect(showAllButtons).toHaveLength(2); // both start collapsed, independently
  await userEvent.click(showAllButtons[0]);
  // Expanding one duplicate-titled section must not touch the other's
  // persisted state — a title-keyed storageKey would collide and expand
  // (or collapse) both at once.
  expect(screen.queryAllByText(/show all 10/i)).toHaveLength(1);
  expect(localStorage.getItem("atrb:generic:dup-one")).toContain('"expanded":true');
  expect(localStorage.getItem("atrb:generic:dup-two")).toBeNull();
});

test("a pinned ticker (shared pins pref) stays first in the scorecard despite an active score sort", () => {
  localStorage.setItem("atrb:pins", JSON.stringify(["MSFT"]));
  localStorage.setItem(
    "atrb:scorecard",
    JSON.stringify({ sortKey: "score_sum", sortDir: "desc", expanded: false, hiddenCols: [] }),
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
  expect(screen.getAllByText("Risk-on, 3rd night").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("VIX level")).toBeInTheDocument();
});
