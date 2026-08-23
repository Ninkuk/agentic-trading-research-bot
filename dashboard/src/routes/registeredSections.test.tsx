// Parametrized smoke test: every section id the fixture carries
// (other than "candidates", covered separately by Main.test.tsx's error
// case) must render through Main without throwing, and show one of the
// forms SectionShell/its registered component can produce — a table, a
// tile grid, a text report, the section's own `empty` string, or an
// `error` note. This is the broad coverage net; component-specific
// behavior (Scorecard's filter/flag/link, SignalEfficacy's pill, Research
// Reopens' thesis link) gets its own dedicated test file instead of living
// here, since a bare "didn't throw" assertion can't tell a dedicated
// component apart from GenericSection for the sections whose export is
// itself already a plain columns+rows/tiles/text_lines bag.

import { render, within } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc, Section } from "../types";
import { Main } from "./Main";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
});

type Outcome = "error" | "empty" | "tiles" | "text" | "rows";

function outcomeOf(sec: Section): Outcome {
  if (sec.error) return "error";
  const hasRows = Array.isArray(sec.rows) && sec.rows.length > 0;
  if (!hasRows && sec.empty !== undefined) return "empty";
  // "equity-curve" carries its data as `curve`, not `rows` — it renders a
  // chart, so it lands in the same svg-accepting branch as regime-timeline.
  if (sec.curve) return "rows";
  if (sec.rows) return "rows";
  if (sec.tiles && sec.tiles.length > 0) return "tiles";
  if (sec.text_lines && sec.text_lines.length > 0) return "text";
  return "empty";
}

const ids = Object.keys(doc.sections);

test.each(ids)('section "%s" renders via its registered component without throwing', (id) => {
  render(<Main doc={doc} />);
  const region = document.getElementById(id);
  expect(region).not.toBeNull();
  const sec = doc.sections[id];
  const outcome = outcomeOf(sec);
  const scope = within(region as HTMLElement);

  switch (outcome) {
    case "error":
      expect(scope.getByText(sec.error as string)).toBeInTheDocument();
      break;
    case "empty":
      expect(scope.getByText(sec.empty ?? "no rows yet")).toBeInTheDocument();
      break;
    case "tiles":
      expect(region?.querySelectorAll(".tile").length).toBeGreaterThan(0);
      break;
    case "text":
      // TextReport parses the scorecard report into tables; its fallback for
      // an unparseable format is the raw <pre> — accept either rendering.
      expect(region?.querySelector("table, pre")).not.toBeNull();
      break;
    case "rows":
      // Most row-carrying sections render through DataTable (a <table>);
      // the chart sections ("regime-timeline" from `rows`, "equity-curve"
      // from `curve`) draw an <svg> instead — so accept either.
      expect(region?.querySelector("table, svg")).not.toBeNull();
      break;
  }
});
