// sectionCells: the shared lab-design cell heuristics. The advisor
// dollar/percent expectations carry over verbatim from the retired
// advisorCell — the identical market value must never read "$1,980.50" on
// the ticker page and "1980.5" on the main page.

import { render, screen } from "@testing-library/react";
import type { Column, Row } from "../types";
import { sectionCell, visibleColumns } from "./sectionCells";

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

test("hit rate folds its CI into one stacked cell", () => {
  render(<>{sectionCell(ROW, col("hit_rate"))}</>);
  expect(screen.getByText("58%")).toBeInTheDocument();
  expect(screen.getByText("CI 49–67")).toBeInTheDocument();
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
