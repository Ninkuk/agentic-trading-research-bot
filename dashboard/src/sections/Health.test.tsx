import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { SectionShell } from "../ui/SectionShell";
import { Health } from "./Health";

const doc = fixture as unknown as DashboardDoc;

test("unhealthy fixture section renders tiles and both problem rows", () => {
  render(<Health sec={doc.sections["health"]} glossary={doc.glossary} />);
  expect(screen.getByText("runs (24h)")).toBeInTheDocument();
  expect(screen.getByText("jobs loaded")).toBeInTheDocument();
  expect(screen.getByText("cftc.db")).toBeInTheDocument();
  expect(screen.getByText("cboe-stats")).toBeInTheDocument();
});

test("healthy section (empty rows) shows the all-clear line, not a table", () => {
  const sec = {
    ...doc.sections["health"],
    healthy: true,
    rows: [],
  };
  render(<Health sec={sec} glossary={doc.glossary} />);
  expect(
    screen.getByText("All healthy — every job ran clean, every database is fresh."),
  ).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

// Bug class this guards: data.py's `_health` sets `sec.empty` whenever `rows` is empty, and
// SectionShell renders ITS OWN empty state instead of `children` whenever
// `sec.empty !== undefined && !hasRows` (SectionShell.tsx's `showEmpty`) —
// so a healthy night's tiles would silently vanish behind the shell's empty
// card. Proving the tiles survive requires rendering through SectionShell,
// not Health in isolation.
test("healthy state still shows tiles when wrapped in SectionShell, as in production", () => {
  const sec = {
    ...doc.sections["health"],
    healthy: true,
    rows: [],
  };
  render(
    <SectionShell id="health" sec={sec}>
      <Health sec={sec} glossary={doc.glossary} />
    </SectionShell>,
  );
  expect(screen.getByText("runs (24h)")).toBeInTheDocument();
  expect(screen.getByText("jobs loaded")).toBeInTheDocument();
  expect(
    screen.getByText("All healthy — every job ran clean, every database is fresh."),
  ).toBeInTheDocument();
});
