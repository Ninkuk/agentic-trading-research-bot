import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import { Main } from "../routes/Main";
import type { DashboardDoc, Glossary, Section } from "../types";
import { PortfolioVsSpy } from "./PortfolioVsSpy";

const GLOSSARY: Glossary = {};
const sec = fixture.sections["equity-curve"] as unknown as Section;

// The headline is the exporter's plain-English tiles, never the raw
// curve_summary fields: "TWR" and "excess" are jargon the About copy explains.
test("renders the exporter's tiles as the headline, no jargon", () => {
  const { container } = render(
    <PortfolioVsSpy sec={sec} glossary={GLOSSARY} />,
  );
  expect(container.querySelectorAll(".tile").length).toBe(3);
  expect(screen.getByText("+12.50%")).toBeInTheDocument();
  expect(screen.getByText("Your picks")).toBeInTheDocument();
  expect(screen.getByText("Cash")).toBeInTheDocument();
  expect(screen.queryByText(/TWR|excess/)).toBeNull();
});

test("the verdict chip carries the ahead-or-behind call", () => {
  render(<Main doc={fixture as unknown as DashboardDoc} />);
  expect(screen.getByText(/Ahead of SPY by 10\.9 points/)).toBeInTheDocument();
});

// The coverage note sits in the chart's legend row, bottom-right, at the
// legend's size — a footnote, not a fifth headline stat.
test("renders the coverage footnote inside the chart legend row", () => {
  const { container } = render(
    <PortfolioVsSpy sec={sec} glossary={GLOSSARY} />,
  );
  const note = screen.getByText(/2 positions · 3 trading days/);
  expect(note.closest(".equity-curve-legend")).not.toBeNull();
  expect(note.className).toContain("ml-auto");
  expect(container.querySelector(".tiles")?.textContent).not.toMatch(
    /positions/,
  );
});

test("renders nothing without curve data (SectionShell owns empty/error)", () => {
  const { container } = render(
    <PortfolioVsSpy sec={{ title: "x" }} glossary={GLOSSARY} />,
  );
  expect(container.firstChild).toBeNull();
});

// The half the component deliberately does NOT implement: data.py's empty
// (fewer than two trading days with a position) and error (missing DB)
// bodies omit `curve` entirely, and the component returning null is only correct
// because SectionShell renders those states around it. Asserted through
// Main so the whole chain — registry entry, shell, component — is covered.
const degraded = (body: Partial<Section>): DashboardDoc => ({
  ...(fixture as unknown as DashboardDoc),
  sections: {
    ...(fixture as unknown as DashboardDoc).sections,
    "equity-curve": {
      title: "Portfolio vs SPY",
      kicker: "Track record",
      ...body,
    },
  },
});

test("empty body renders the shell's empty note, no chart", () => {
  render(
    <Main
      doc={degraded({
        empty: "needs at least two trading days with a journaled position",
      })}
    />,
  );
  expect(
    screen.getByText(/needs at least two trading days/),
  ).toBeInTheDocument();
  expect(
    document.getElementById("equity-curve")?.querySelector(".recharts-surface"),
  ).toBeNull();
});

test("error body renders the shell's error note, no chart", () => {
  render(<Main doc={degraded({ error: "scorer.db missing" })} />);
  expect(screen.getByText(/scorer.db missing/)).toBeInTheDocument();
  expect(
    document.getElementById("equity-curve")?.querySelector(".recharts-surface"),
  ).toBeNull();
});

// --- Range selector -------------------------------------------------------
// The fixture's curve is three closes, 07-31 → 08-05, so only 1D shows less
// than ALL; every calendar range reaches back past inception and is
// rendered disabled rather than repeating ALL.

import { fireEvent, within } from "@testing-library/react";

function selector() {
  return screen.getByRole("radiogroup", { name: /range/i });
}

test("renders the Robinhood range row with ALL selected and history-less ranges disabled", () => {
  render(<PortfolioVsSpy sec={sec} glossary={GLOSSARY} />);
  const radios = within(selector()).getAllByRole("radio");
  expect(radios.map((r) => r.textContent)).toEqual([
    "1D",
    "1W",
    "1M",
    "3M",
    "YTD",
    "1Y",
    "ALL",
  ]);
  const byName = Object.fromEntries(radios.map((r) => [r.textContent, r]));
  expect(byName.ALL).toHaveAttribute("aria-checked", "true");
  expect(byName["1D"]).toBeEnabled();
  for (const k of ["1W", "1M", "3M", "YTD", "1Y"]) {
    expect(byName[k]).toBeDisabled();
  }
});

test("selecting 1D windows the chart and recomputes the tiles from the window", () => {
  const { container } = render(
    <PortfolioVsSpy sec={sec} glossary={GLOSSARY} />,
  );
  fireEvent.click(within(selector()).getByRole("radio", { name: "1D" }));
  // 112.5 / 109.72 − 1 = +2.53%; SPY 101.59 / 101.0 − 1 = +0.58%; cash +0.01%.
  expect(screen.getByText("+2.53%")).toBeInTheDocument();
  expect(screen.getByText("+0.58%")).toBeInTheDocument();
  expect(screen.getByText("+0.01%")).toBeInTheDocument();
  expect(screen.queryByText("+12.50%")).toBeNull();
  // The x-axis now starts at the window's base, not inception.
  const ticks = [...container.querySelectorAll(".recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value")].map((t) => t.textContent);
  expect(ticks).not.toContain("07-31");
  expect(ticks).toContain("08-04");
});

test("returning to ALL restores the exporter's exact tiles", () => {
  render(<PortfolioVsSpy sec={sec} glossary={GLOSSARY} />);
  fireEvent.click(within(selector()).getByRole("radio", { name: "1D" }));
  fireEvent.click(within(selector()).getByRole("radio", { name: "ALL" }));
  expect(screen.getByText("+12.50%")).toBeInTheDocument();
  expect(screen.getByText("+1.59%")).toBeInTheDocument();
});

// The footnote's trading days follow the window by `session` (ALL keeps the
// exporter's count); positions is the book as held today, not a window
// quantity, so it stays.
test("the coverage footnote counts the window's trading days", () => {
  render(<PortfolioVsSpy sec={sec} glossary={GLOSSARY} />);
  fireEvent.click(within(selector()).getByRole("radio", { name: "1D" }));
  expect(screen.getByText(/2 positions · 2 trading days/)).toBeInTheDocument();
  fireEvent.click(within(selector()).getByRole("radio", { name: "ALL" }));
  expect(screen.getByText(/2 positions · 3 trading days/)).toBeInTheDocument();
});

// The chip lives in SectionShell's header, outside this component, so the
// window re-states it through the shell's verdict context. Asserted
// through Main so the whole chain is covered.
test("the header chip follows the window and returns on ALL", () => {
  render(<Main doc={fixture as unknown as DashboardDoc} />);
  const chip = () => document.querySelector("#equity-curve .verdict-chip");
  expect(chip()?.textContent).toBe("Ahead of SPY by 10.9 points since Jul 31");
  fireEvent.click(within(selector()).getByRole("radio", { name: "1D" }));
  // 112.5/109.72 − 101.59/101.0 = 2.53% − 0.58% = 1.9 points since Aug 4.
  expect(chip()?.textContent).toBe("Ahead of SPY by 1.9 points since Aug 4");
  fireEvent.click(within(selector()).getByRole("radio", { name: "ALL" }));
  expect(chip()?.textContent).toBe("Ahead of SPY by 10.9 points since Jul 31");
});
