import { parseScorecardHeadline } from "./scorecardHeadline";

// Representative live report (scorer/scorecard.py build_report, 2026-08).
const LIVE = `=== Trader Decision-Quality Scorecard — 2026-08 ===

Filter edge (acted vs passed, by horizon)
  horizon | response         | n  | avg_dir_excess | avg_fwd_return
        5 | passed           |  3 | insufficient data (n=3) | insufficient data (n=3)
        5 | passed_inferred  | 62 | 0.0390         | 0.0327
       10 | passed_inferred  | 47 | 0.1070         | 0.1455
       21 | passed_inferred  | 33 | -0.0723        | 0.0384

Execution cost (acted decisions, by horizon)
  horizon | n  | avg_entry_slippage | avg_fill_lag_days
        5 |  7 | -1.40%             | 1.00
       10 |  7 | -1.40%             | 1.00

Alignment (acted decisions, by horizon)
  horizon | agreed | contrarian | no opinion
        5 |      2 |          5 |          0
       10 |      2 |          5 |          0

Portfolio vs SPY and cash (time-weighted)
  window     | portfolio TWR | SPY      | excess   | cash (DFF)
  inception  |         3.01% |    1.62% |    1.39% | 0.50%
  21d        |         2.87% |    1.13% |    1.74% | 0.45%
  63d        | insufficient data (n=24 trading days)
  coverage: 26 ledger dates 2026-07-05..2026-08-26, 13 trading days missing`.split("\n");

test("lifts every headline from the live report shape", () => {
  expect(parseScorecardHeadline(LIVE)).toEqual({
    twr: { portfolio: 3.01, spy: 1.62, excess: 1.39 },
    filterEdge: { horizon: 10, excess: 0.107 },
    slippage: -1.4,
    alignment: { horizon: 5, agreed: 2, contrarian: 5 },
  });
});

test("older alignment column names and a missing TWR block still parse", () => {
  const lines = [
    "Alignment (acted decisions, by horizon)",
    "  horizon | aligned=1 | aligned=0 | aligned=NULL",
    "       21 |        10 |         2 |            0",
  ];
  expect(parseScorecardHeadline(lines)).toEqual({
    twr: null,
    filterEdge: null,
    slippage: null,
    // no horizon-5 row: the shortest horizon stands in
    alignment: { horizon: 21, agreed: 10, contrarian: 2 },
  });
});

test("prose in numeric cells and unknown blocks yield null, not NaN", () => {
  const lines = [
    "Filter edge (acted vs passed, by horizon)",
    "  horizon | response | n | avg_dir_excess | avg_fwd_return",
    "        5 | passed_inferred | 3 | insufficient data (n=3) | insufficient data (n=3)",
  ];
  expect(parseScorecardHeadline(lines)).toBeNull();
  expect(parseScorecardHeadline(["free-form", "lines"])).toBeNull();
});
