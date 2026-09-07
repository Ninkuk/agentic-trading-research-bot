import { render, screen } from "@testing-library/react";
import fixture from "../fixtures/data.json";
import type { DashboardDoc, Tile } from "../types";
import { TileCharts } from "./TileCharts";
import { hasChart } from "./tileHistory";

const doc = fixture as unknown as DashboardDoc;
const macro = doc.sections["macro-drivers"].tiles ?? [];

function annual(label: string, values: number[]): Tile {
  return { label, value: values.at(-1), history: values.map((value, i) => ({ date: String(2007 + i), value })) };
}

test("one column per tile up to four, each history tile with a chart", () => {
  const { container } = render(<TileCharts tiles={macro} />);
  expect(container.firstChild).toHaveClass("md:grid-cols-3");
  expect(screen.getByText("Fear index (VIX) · calm")).toBeInTheDocument();
  expect(container.querySelectorAll("[data-chart]")).toHaveLength(3);
});

test("the junk-bond cutoff at 4.0 is drawn beside a series topping at 3.4; the VIX 15 line is not", () => {
  const { container } = render(<TileCharts tiles={macro} />);
  // Fixture: every driver runs 1.1→3.4 (span 2.3, half = 1.15). hy_spread's
  // 4.0 is 0.6 above and t10y2y's 0.0 is 1.1 below — both drawn; vix's 15 is not.
  expect(container.querySelectorAll(".driver-threshold")).toHaveLength(2);
  expect(container.textContent).toContain("wide");
  expect(container.textContent).not.toContain("nervous");
});

test("six grain tiles wrap as three columns and label the axis with crop years", () => {
  const tiles = ["Corn", "Soy", "Wheat"].flatMap((c) => [
    annual(`${c} stockpile`, [1, 2, 3, 4, 5]),
    annual(`${c} harvest`, [5, 4, 3, 2, 1]),
  ]);
  const { container } = render(<TileCharts tiles={tiles} />);
  expect(container.firstChild).toHaveClass("md:grid-cols-3");
  expect(container.querySelectorAll("[data-chart]")).toHaveLength(6);
  const ticks = Array.from(
    container.querySelectorAll(".recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value"),
  ).map((t) => t.textContent);
  expect(ticks.slice(0, 3)).toEqual(["2007", "2009", "2011"]);
});

test("a tile without enough history keeps its place in the grid, chart-less", () => {
  const tiles: Tile[] = [
    { label: "Overnight lending rate (SOFR)", value: 3.66, history: [{ date: "2026-07-08", value: 3.66 }] },
    { label: "Gap between them", value: 0.01, band: "calm" },
    annual("Fed's holdings", [6.1, 6.2, 6.3, 6.4]),
  ];
  expect(tiles.map(hasChart)).toEqual([false, false, true]);
  const { container } = render(<TileCharts tiles={tiles} />);
  expect(container.querySelectorAll(".tile")).toHaveLength(3);
  expect(container.querySelectorAll("[data-chart]")).toHaveLength(1);
});
