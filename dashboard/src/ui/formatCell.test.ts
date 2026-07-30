// formatCell: the default plain-text cell path every table falls through
// to. (The advisor dollar/percent columns are covered in
// sectionCells.test.tsx — the shared lab heuristics own them now.)

import { formatCell } from "./formatCell";

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
