import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import { KICKERS, type DashboardDoc, type Kicker } from "../types";
import { AppShell } from "./AppShell";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
});

function navLinks() {
  const nav = screen.getByRole("navigation", { name: /sections/i });
  return within(nav).getAllByRole("link");
}

test("sidebar lists Summary first, then every strand in order, each linking to its hash route", () => {
  render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  const links = navLinks();
  expect(links.map((l) => l.textContent)).toEqual(["Summary", ...KICKERS]);
  expect(links[0]).toHaveAttribute("href", "#/");
  expect(links[KICKERS.indexOf("Track record") + 1]).toHaveAttribute(
    "href",
    "#/track-record",
  );
  expect(screen.getByText("body")).toBeInTheDocument();
});

test("the active item follows the route: Summary on main, the strand on a strand route", () => {
  const { rerender } = render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Summary" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  rerender(
    <AppShell doc={doc} route={{ route: "strand", id: "signals" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Signals" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(screen.getByRole("link", { name: "Summary" })).not.toHaveAttribute(
    "aria-current",
  );
});

test("a bare section anchor marks the strand that holds the section", () => {
  render(
    <AppShell doc={doc} route={{ route: "section", id: "equity-curve" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Track record" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("the active strand opens to its live sections, each linking to its anchor; the rest start closed", () => {
  render(
    <AppShell doc={doc} route={{ route: "strand", id: "macro" }}>
      <p>body</p>
    </AppShell>,
  );
  const macro = screen
    .getByRole("link", { name: "Macro" })
    .closest("li") as HTMLElement;
  const subLinks = within(macro).getAllByRole("link").slice(1);
  expect(subLinks.length).toBeGreaterThan(1);
  expect(subLinks.map((l) => l.getAttribute("href"))).toContain("#regime");
  expect(within(macro).getByRole("link", { name: "Regime" })).toHaveAttribute(
    "title",
    "Regime",
  );
  const signals = screen
    .getByRole("link", { name: "Signals" })
    .closest("li") as HTMLElement;
  expect(within(signals).getAllByRole("link")).toHaveLength(1);
  // Nothing is current before the first observation (no IntersectionObserver under jsdom).
  expect(macro.querySelector('[aria-current="location"]')).toBeNull();
});

test("the chevron opens a closed strand and closes an open one; landing on a strand reopens it", async () => {
  const user = userEvent.setup();
  const { rerender } = render(
    <AppShell doc={doc} route={{ route: "strand", id: "macro" }}>
      <p>body</p>
    </AppShell>,
  );
  const signals = () =>
    screen.getByRole("link", { name: "Signals" }).closest("li") as HTMLElement;
  await user.click(screen.getByRole("button", { name: "Expand Signals" }));
  expect(within(signals()).getAllByRole("link").length).toBeGreaterThan(1);
  await user.click(screen.getByRole("button", { name: "Collapse Signals" }));
  expect(within(signals()).getAllByRole("link")).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "Collapse Macro" }));
  const macro = () =>
    screen.getByRole("link", { name: "Macro" }).closest("li") as HTMLElement;
  expect(within(macro()).getAllByRole("link")).toHaveLength(1);
  rerender(
    <AppShell doc={doc} route={{ route: "strand", id: "signals" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(within(signals()).getAllByRole("link").length).toBeGreaterThan(1);
  // Macro stays as the reader left it.
  expect(within(macro()).getAllByRole("link")).toHaveLength(1);
});

test("a grouped strand expands to its publishers, and a group anchor lights the strand", () => {
  const columns = [
    { key: "x", label: "X", numeric: false, direction: null, term: null },
  ];
  const rows = [{ x: "a" }];
  const sections = { ...doc.sections };
  for (const [id, sec] of Object.entries(sections)) {
    if (sec.kicker === "Sources")
      sections[id] = { ...sec, columns, rows, empty: undefined };
  }
  render(
    <AppShell
      doc={{ ...doc, sections }}
      route={{ route: "section", id: "sources-sec" }}
    >
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  const sources = screen
    .getByRole("link", { name: "Sources" })
    .closest("li") as HTMLElement;
  const subLinks = within(sources).getAllByRole("link").slice(1);
  expect(subLinks.map((l) => l.textContent)).toEqual([
    "Treasury",
    "NY Fed",
    "FRED",
    "CFTC",
    "FINRA",
    "SEC",
    "CBOE",
    "Earnings",
    "EIA",
    "USDA",
    "Reddit",
  ]);
  expect(within(sources).getByRole("link", { name: "SEC" })).toHaveAttribute(
    "href",
    "#sources-sec",
  );
});

test("the ticker route highlights nothing", () => {
  render(
    <AppShell doc={doc} route={{ route: "ticker", symbol: "AAPL" }}>
      <p>body</p>
    </AppShell>,
  );
  for (const l of navLinks()) expect(l).not.toHaveAttribute("aria-current");
});

test("an Other item appears only when a section's kicker is unknown", () => {
  const { rerender } = render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.queryByRole("link", { name: "Other" })).not.toBeInTheDocument();
  const drifted: DashboardDoc = {
    ...doc,
    sections: {
      ...doc.sections,
      stray: { title: "Stray", kicker: "Vibes" as unknown as Kicker },
    },
  };
  rerender(
    <AppShell doc={drifted} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Other" })).toHaveAttribute(
    "href",
    "#/other",
  );
});

test("the masthead trigger collapses the rail and the choice persists in prefs", async () => {
  render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  const rail = document.querySelector('[data-slot="sidebar"]') as HTMLElement;
  expect(rail).toHaveAttribute("data-state", "expanded");
  // The rail edge is a second "Toggle Sidebar" button (tabIndex -1); the
  // masthead one is the trigger.
  await userEvent.click(
    document.querySelector('[data-slot="sidebar-trigger"]') as HTMLElement,
  );
  expect(rail).toHaveAttribute("data-state", "collapsed");
  expect(localStorage.getItem("atrb:sidebar-open")).toBe("false");
});

test("the masthead still carries the edition date and theme toggle", () => {
  render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByText(doc.edition_date)).toBeInTheDocument();
  // Single-select ToggleGroup items are radios.
  expect(
    screen.getByRole("radio", { name: /dark theme/i }),
  ).toBeInTheDocument();
});
