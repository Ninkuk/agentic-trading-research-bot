
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { matches, universe } from "./suggest";

const doc = fixture as unknown as DashboardDoc;

test("universe joins the scorecard, the screen and the researched names, sorted, with the call", () => {
  const d: DashboardDoc = {
    ...doc,
    sections: {
      scorecard: { rows: [{ symbol: "MSFT" }, { symbol: "AAPL" }] },
      candidates: { rows: [{ symbol: "KTB" }, { symbol: "AAPL" }] },
      research: { rows: [{ ticker: "KTB", call: "BUY" }, { ticker: "ZZZ", call: "PASS" }] },
    },
  };
  expect(universe(d)).toEqual([
    { symbol: "AAPL", call: null },
    { symbol: "KTB", call: "buy" },
    { symbol: "MSFT", call: null },
    { symbol: "ZZZ", call: "pass" },
  ]);
  expect(universe({ ...doc, sections: { scorecard: { error: "no composite.db" } } })).toEqual([]);
});

test("matches lists symbols on the typed prefix, capped, none for nothing typed", () => {
  const known = universe(doc);
  expect(known.length).toBeGreaterThan(0);
  expect(matches(known, "")).toEqual([]);
  const a = matches(known, "A", 3);
  expect(a.length).toBeGreaterThan(0);
  expect(a.length).toBeLessThanOrEqual(3);
  for (const k of a) expect(k.symbol.startsWith("A")).toBe(true);
  expect(matches(known, "A", 1).length).toBe(1);
  expect(matches(known, "QQQQQQ")).toEqual([]);
});
