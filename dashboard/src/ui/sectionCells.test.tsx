// sectionCells: the shared lab-design cell heuristics. The advisor
// dollar/percent expectations carry over verbatim from the retired
// advisorCell — the identical market value must never read "$1,980.50" on
// the ticker page and "1980.5" on the main page.

import { render, screen } from "@testing-library/react";
import type { Column, Row } from "../types";
import { makeSectionCell, sectionCell, visibleColumns } from "./sectionCells";

function col(key: string, numeric = true): Column {
  return { key, label: key, numeric, direction: null, term: null };
}

const ROW: Row = {
  symbol: "AAPL",
  market_value: 1980.5,
  price: 198.05,
  heat_dollars: 42.1,
  cap_dollars: 4950,
  heat_pct: 0.25,
  weight_pct: 2.35,
  score_sum: -2,
  coverage: 0.8,
  worst_staleness_days: 1,
  in_portfolio: true,
  hit_rate: 0.58,
  hit_ci_lo: 0.49,
  hit_ci_hi: 0.67,
  recommendation: "keep",
  avg_directional_excess: 0.012,
};

test("dollar columns format as USD with grouped thousands", () => {
  expect(sectionCell(ROW, col("market_value"))).toBe("$1,980.50");
  expect(sectionCell(ROW, col("price"))).toBe("$198.05");
  expect(sectionCell(ROW, col("heat_dollars"))).toBe("$42.10");
  expect(sectionCell(ROW, col("cap_dollars"))).toBe("$4,950.00");
});

test("percent-unit columns keep two decimals (0.25 must not round to 0.3%)", () => {
  expect(sectionCell(ROW, col("heat_pct"))).toBe("0.25%");
  expect(sectionCell(ROW, col("weight_pct"))).toBe("2.35%");
});

test("fraction columns render as whole percents", () => {
  expect(sectionCell(ROW, col("coverage"))).toBe("80%");
});

test("score renders tinted and signed; staleness gains its unit", () => {
  render(<>{sectionCell(ROW, col("score_sum"))}</>);
  const score = screen.getByText("−2");
  expect(score).toHaveClass("tag-off");
  expect(sectionCell(ROW, col("worst_staleness_days"))).toBe("1d");
});

test("hit rate renders as a range mark: rate as text, CI digits in the title only", () => {
  const { container } = render(<>{sectionCell(ROW, col("hit_rate"))}</>);
  expect(screen.getByText("58%")).toBeInTheDocument();
  expect(container.querySelector("svg circle.range-dot")).not.toBeNull();
  expect(container.querySelector("span[title]")?.getAttribute("title")).toBe("58%, CI 49–67%");
  expect(container.querySelector("span.font-mono")?.textContent).toBe("58%");
});

test("null_rate (else drift_baseline, else baseline) becomes the range mark's tick", () => {
  const withNull = render(<>{sectionCell({ ...ROW, null_rate: 0.5, baseline: 0.3 }, col("hit_rate"))}</>);
  expect(withNull.container.querySelector("span[title]")?.getAttribute("title")).toBe("58%, CI 49–67%, beats 50%");
  const withDrift = render(<>{sectionCell({ ...ROW, drift_baseline: 0.55, baseline: 0.3 }, col("hit_rate"))}</>);
  expect(withDrift.container.querySelector("span[title]")?.getAttribute("title")).toBe("58%, CI 49–67%, beats 55%");
  const withBaseline = render(<>{sectionCell({ ...ROW, baseline: 0.3 }, col("hit_rate"))}</>);
  expect(withBaseline.container.querySelector("line.range-tick")).not.toBeNull();
  expect(render(<>{sectionCell(ROW, col("hit_rate"))}</>).container.querySelector("line.range-tick")).toBeNull();
});

test("makeSectionCell scales excess and weight/heat marks to the table's column max", () => {
  const rows: Row[] = [
    { ...ROW, avg_directional_excess: 0.012, weight_pct: 2.35, heat_dollars: 42.1 },
    { ...ROW, avg_directional_excess: -0.024, weight_pct: 4.7, heat_dollars: 10 },
    { ...ROW, avg_directional_excess: 0.006, weight_pct: 1, heat_dollars: 84.2 },
  ];
  const cell = makeSectionCell(rows);
  const { container } = render(
    <>
      <span data-testid="ex">{cell(rows[0], col("avg_directional_excess"))}</span>
      <span data-testid="neg">{cell(rows[1], col("avg_directional_excess"))}</span>
      <span data-testid="w">{cell(rows[1], col("weight_pct"))}</span>
      <span data-testid="h">{cell(rows[0], col("heat_dollars"))}</span>
    </>,
  );
  expect(container.querySelector('[data-testid="ex"] path.diverging-bar--up')).not.toBeNull();
  expect(container.querySelector('[data-testid="neg"] path.diverging-bar--down')).not.toBeNull();
  expect(screen.getByText("+1.2%").className).not.toMatch(/tag-/);
  // The column max (|−0.024|) fills its half-axis; +0.012 is half of it.
  const len = (sel: string) => {
    const d = container.querySelector(`${sel} path.diverging-bar`)?.getAttribute("d") ?? "";
    const x = [...d.matchAll(/[MHA]\s*(?:[\d.]+,[\d.]+ 0 0 [01] )?(-?[\d.]+)/g)].map((m) => Number(m[1]));
    return Math.max(...x) - Math.min(...x);
  };
  expect(len('[data-testid="ex"]')).toBeCloseTo(len('[data-testid="neg"]') / 2, 1);
  expect(container.querySelector('[data-testid="w"] path.bar-fill')).not.toBeNull();
  expect(screen.getByText("4.70%")).toBeInTheDocument();
  expect(container.querySelector('[data-testid="h"] path.bar-fill')).not.toBeNull();
  expect(screen.getByText("$42.10")).toBeInTheDocument();
});

test("under three valid values the scaled keys keep their digits (no mark)", () => {
  const cell = makeSectionCell([ROW, { ...ROW, avg_directional_excess: null }]);
  const { container } = render(<>{cell(ROW, col("avg_directional_excess"))}</>);
  expect(container.querySelector("svg")).toBeNull();
  expect(screen.getByText("+1.2%")).toHaveClass("tag-on");
  expect(cell(ROW, col("weight_pct"))).toBe("2.35%");
});

test("recommendation and held render as pills; signed excess is tinted", () => {
  render(
    <>
      {sectionCell(ROW, col("recommendation"))}
      {sectionCell(ROW, col("in_portfolio"))}
      {sectionCell(ROW, col("avg_directional_excess"))}
    </>,
  );
  // shadcn Badge component (data-slot) with the tinted rec-- marker class.
  expect(screen.getByText("keep")).toHaveAttribute("data-slot", "badge");
  expect(screen.getByText("keep")).toHaveClass("rec--up");
  expect(screen.getByText("held")).toHaveAttribute("data-slot", "badge");
  expect(screen.getByText("+1.2%")).toHaveClass("tag-on");
});

test("unknown columns fall through to the default cell formatting", () => {
  expect(sectionCell(ROW, col("missing"))).toBe("—");
});

test("visibleColumns drops the CI columns the hit-rate cell absorbs", () => {
  const cols = [col("signal_id", false), col("hit_ci_lo"), col("hit_ci_hi"), col("via_crosswalk"), col("hit_rate")];
  expect(visibleColumns(cols).map((c) => c.key)).toEqual(["signal_id", "hit_rate"]);
});

test("number-array cells render as a sparkline, booleans as tinted pills by key semantics", () => {
  const row: Row = {
    history: [1, 2, 3],
    beat_benchmark: true,
    atr_stale: true,
    closed: true,
    fwd_return: -0.012,
    baseline: 0.55,
  };
  const { container } = render(
    <>
      <span>{sectionCell(row, col("history", false))}</span>
      <span>{sectionCell(row, col("beat_benchmark", false))}</span>
      <span>{sectionCell(row, col("atr_stale", false))}</span>
      <span>{sectionCell(row, col("closed", false))}</span>
      <span>{sectionCell(row, col("fwd_return"))}</span>
      <span>{sectionCell(row, col("baseline"))}</span>
    </>,
  );
  expect(container.querySelector("svg.sparkline")).not.toBeNull();
  const yes = screen.getAllByText("yes");
  expect(yes[0].className).toMatch(/bool--good/); // a beaten benchmark is good
  expect(yes[1].className).toMatch(/bool--bad/); // a stale ATR is bad
  expect(yes[2].className).not.toMatch(/bool/); // unknown key (`closed`): plain text
  expect(screen.getByText("−1.2%")).toBeInTheDocument();
  expect(screen.getByText("55%")).toBeInTheDocument();
});
