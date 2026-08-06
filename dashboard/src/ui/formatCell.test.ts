// formatCell: the default plain-text cell path every table falls through
// to. (The advisor dollar/percent columns are covered in
// sectionCells.test.tsx — the shared lab heuristics own them now.)

import { formatCell, humanizeId, isMachineId } from "./formatCell";

test("formatCell caps numbers at 2 decimal places", () => {
  expect(formatCell(0.6153846153846154)).toBe("0.62");
  expect(formatCell(3)).toBe("3"); // integers gain no trailing ".00"
  expect(formatCell(1.5)).toBe("1.5");
});

test("formatCell abbreviates millions and billions", () => {
  expect(formatCell(14967000806.137735)).toBe("14.97B");
  expect(formatCell(2500000)).toBe("2.5M");
  expect(formatCell(-1200000000)).toBe("−1.2B");
  expect(formatCell(999999)).toBe("999999"); // below the 1e6 threshold — untouched
});

test("formatCell renders negatives with a typographic minus, signed off the rounded value", () => {
  expect(formatCell(-2.456)).toBe("−2.46");
  expect(formatCell(-0.004)).toBe("0"); // rounds to zero — no dangling minus
});

test("machine ids humanize to words with known abbreviations uppercased", () => {
  expect(humanizeId("si_days_to_cover")).toBe("SI days to cover");
  expect(humanizeId("sv_ratio_spike")).toBe("SV ratio spike");
  expect(humanizeId("risk_on")).toBe("Risk on");
  expect(humanizeId("q2-print-nrr-and-api-monetization")).toBe("Q2 print NRR and API monetization");
});

test("formatCell humanizes machine ids but leaves ordinary strings alone", () => {
  expect(formatCell("ftd_persistent")).toBe("FTD persistent");
  expect(formatCell("keep")).toBe("keep"); // single word, not an id
  expect(formatCell("BRK-B")).toBe("BRK-B"); // one hyphen + uppercase: not a slug
});

test("isMachineId requires separators, so symbols and words pass through", () => {
  expect(isMachineId("risk_on")).toBe(true);
  expect(isMachineId("a-b-c")).toBe(true);
  expect(isMachineId("AAPL")).toBe(false);
  expect(isMachineId("comfortable")).toBe(false);
});
