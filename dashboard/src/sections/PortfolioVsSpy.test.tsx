import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import { Main } from "../routes/Main";
import type { DashboardDoc, Glossary, Section } from "../types";
import { PortfolioVsSpy } from "./PortfolioVsSpy";

const GLOSSARY: Glossary = {};
const sec = fixture.sections["equity-curve"] as unknown as Section;

test("renders summary numbers from curve_summary", () => {
  render(<PortfolioVsSpy sec={sec} glossary={GLOSSARY} />);
  expect(screen.getByText(/TWR 4\.07%/)).toBeInTheDocument();
  expect(screen.getByText(/SPY 1\.59%/)).toBeInTheDocument();
  expect(screen.getByText(/excess 2\.48%/)).toBeInTheDocument();
  expect(screen.getByText(/cash 0\.05%/)).toBeInTheDocument();
});

// cash is the one nullable summary stat (missing fred.db / no DFF coverage);
// null must drop the stat, never render "cash 0.00%" or "cash NaN%".
test("omits the cash stat when curve_summary.cash is null", () => {
  render(
    <PortfolioVsSpy
      sec={{ ...sec, curve_summary: { ...sec.curve_summary!, cash: null } }}
      glossary={GLOSSARY}
    />,
  );
  expect(screen.queryByText(/cash/)).toBeNull();
});

// The stats are read straight off curve_summary (unrounded-derived), never
// recomputed from the 2dp-rounded curve points — recomputing 104.07/100 - 1
// would round-trip to the same 4.07% here, so assert the summary is the
// source by feeding it a value the curve cannot produce.
test("summary stats come from curve_summary, not from the rounded curve", () => {
  render(
    <PortfolioVsSpy
      sec={{ ...sec, curve_summary: { ...sec.curve_summary!, twr: 0.1234 } }}
      glossary={GLOSSARY}
    />,
  );
  expect(screen.getByText(/TWR 12\.34%/)).toBeInTheDocument();
});

test("renders nothing without curve data (SectionShell owns empty/error)", () => {
  const { container } = render(<PortfolioVsSpy sec={{ title: "x" }} glossary={GLOSSARY} />);
  expect(container.firstChild).toBeNull();
});

// The half the component deliberately does NOT implement: data.py's empty
// (fewer than two SPY-measurable dates) and error (orphan transfer) bodies
// omit `curve` entirely, and the component returning null is only correct
// because SectionShell renders those states around it. Asserted through
// Main so the whole chain — registry entry, shell, component — is covered.
const degraded = (body: Partial<Section>): DashboardDoc => ({
  ...(fixture as unknown as DashboardDoc),
  sections: {
    ...(fixture as unknown as DashboardDoc).sections,
    "equity-curve": { title: "Portfolio vs SPY", kicker: "Track record", ...body },
  },
});

test("empty body renders the shell's empty note, no chart", () => {
  render(<Main doc={degraded({ empty: "needs at least two SPY-measurable ledger dates" })} />);
  expect(screen.getByText(/needs at least two SPY-measurable/)).toBeInTheDocument();
  expect(document.getElementById("equity-curve")?.querySelector(".recharts-surface")).toBeNull();
});

test("error body renders the shell's error note, no chart", () => {
  render(<Main doc={degraded({ error: "cannot chart: transfer(s) on 2026-08-01" })} />);
  expect(screen.getByText(/cannot chart: transfer/)).toBeInTheDocument();
  expect(document.getElementById("equity-curve")?.querySelector(".recharts-surface")).toBeNull();
});
