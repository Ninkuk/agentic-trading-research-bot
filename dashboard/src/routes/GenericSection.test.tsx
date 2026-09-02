// GenericSection is the path every exporter-only section takes (no
// dedicated component). It must render tiles AND a table when a section
// carries both, sparkline the number-array columns, fold CI columns into
// the hit-rate cell, and say when the rows are a capped drill-down.

import { render, within } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Main } from "./Main";

const base = fixture as unknown as DashboardDoc;

function docWith(id: string, sec: DashboardDoc["sections"][string]): DashboardDoc {
  return { ...base, sections: { ...base.sections, [id]: sec } };
}

beforeEach(() => {
  localStorage.clear();
});

test("renders tiles above the table, sparklines arrays, and reports the cap", () => {
  const doc = docWith("probe-card", {
    title: "Probe card",
    kicker: "Sources",
    note: "One sentence.",
    about: [{ heading: "How", body: "Because." }],
    tiles: [
      { label: "venues", value: 3 },
      {
        label: "debt",
        value: 5,
        history: [
          { date: "2026-07-01", value: 1 },
          { date: "2026-07-02", value: 2 },
          { date: "2026-07-03", value: 5 },
        ],
      },
    ],
    columns: [
      { key: "symbol", label: "Symbol", numeric: false },
      { key: "hit_rate", label: "Hit rate", numeric: true },
      { key: "hit_ci_lo", label: "CI low", numeric: true },
      { key: "hit_ci_hi", label: "CI high", numeric: true },
      { key: "extreme", label: "Extreme?", numeric: false },
      { key: "beat_benchmark", label: "Beat SPY?", numeric: false },
      { key: "history", label: "Trend", numeric: false },
    ],
    rows: [
      {
        symbol: "GC",
        hit_rate: 0.6,
        hit_ci_lo: 0.5,
        hit_ci_hi: 0.7,
        extreme: true,
        beat_benchmark: false,
        history: [1, 2, 3, 2],
      },
    ],
    total: 40,
  });
  render(<Main doc={doc} />);
  const region = document.getElementById("probe-card") as HTMLElement;
  const scope = within(region);
  expect(region.querySelectorAll(".tile").length).toBe(2);
  expect(region.querySelector("table")).not.toBeNull();
  // The array column became a sparkline.
  expect(scope.getByRole("img", { name: /Trend: 4 points/ })).toBeInTheDocument();
  // CI folded into the hit-rate range mark (digits in its title); no standalone CI headers.
  expect(scope.queryByText("CI low")).toBeNull();
  expect(scope.getByRole("img", { name: "60%, CI 50–70%" })).toBeInTheDocument();
  // Boolean pills read as text with the tint agreeing.
  expect(scope.getByText("yes").className).toMatch(/bool--bad/);
  expect(scope.getByText("no").className).toMatch(/bool--bad/);
  expect(scope.getByText(/showing the newest 1 of 40/)).toBeInTheDocument();
  // The card lands in the Sources strand.
  expect(document.getElementById("sources")?.contains(document.getElementById("probe-card"))).toBe(true);
});

test("tiles-only section renders its tiles and no table", () => {
  const doc = docWith("tiles-only", {
    title: "Tiles only",
    kicker: "Sources",
    note: "One sentence.",
    tiles: [{ label: "10-year", value: 4.2, band: "2026-07-08" }],
  });
  render(<Main doc={doc} />);
  const region = document.getElementById("tiles-only") as HTMLElement;
  expect(region.querySelectorAll(".tile").length).toBe(1);
  expect(region.querySelector("table")).toBeNull();
});
