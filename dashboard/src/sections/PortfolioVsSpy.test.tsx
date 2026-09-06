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
