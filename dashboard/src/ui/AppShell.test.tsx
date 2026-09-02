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
  expect(links[KICKERS.indexOf("Track record") + 1]).toHaveAttribute("href", "#/track-record");
  expect(screen.getByText("body")).toBeInTheDocument();
});

test("the active item follows the route: Summary on main, the strand on a strand route", () => {
  const { rerender } = render(
    <AppShell doc={doc} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Summary" })).toHaveAttribute("aria-current", "page");
  rerender(
    <AppShell doc={doc} route={{ route: "strand", id: "signals" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Signals" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Summary" })).not.toHaveAttribute("aria-current");
});

test("a bare section anchor marks the strand that holds the section", () => {
  render(
    <AppShell doc={doc} route={{ route: "section", id: "equity-curve" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Track record" })).toHaveAttribute("aria-current", "page");
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
    sections: { ...doc.sections, stray: { title: "Stray", kicker: "Vibes" as unknown as Kicker } },
  };
  rerender(
    <AppShell doc={drifted} route={{ route: "main" }}>
      <p>body</p>
    </AppShell>,
  );
  expect(screen.getByRole("link", { name: "Other" })).toHaveAttribute("href", "#/other");
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
  await userEvent.click(document.querySelector('[data-slot="sidebar-trigger"]') as HTMLElement);
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
  expect(screen.getByRole("radio", { name: /dark theme/i })).toBeInTheDocument();
});
