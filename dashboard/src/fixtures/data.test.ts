import { KICKERS, type DashboardDoc } from "../types";
import fixture from "./data.json";

// JSON imports lose literal narrowing — a JSON "on" reads back as `string`,
// not the `Tone` union, so `DashboardDoc` itself can never be the direct
// target of a fixture assignment without a permanent false positive on
// every literal-typed field (Tone, ColumnDirection). `Loosen` widens just
// those string-literal types to `string`, leaving every other shape
// (arrays, optionality, object structure) exactly as declared — so this
// check fails only on REAL structural drift between the fixture and
// DashboardDoc (e.g. a field the schema can't represent at all, like the
// scorecard `history` number-array this test was added to guard), not on
// TypeScript's inherent JSON-typing gap.
type Loosen<T> = T extends readonly (infer U)[]
  ? Loosen<U>[]
  : T extends string
    ? string
    : T extends object
      ? { [K in keyof T]: Loosen<T[K]> }
      : T;

// Type-only: if `data.json` drifts from `DashboardDoc`'s shape (a field the
// type can't hold, or a required field the fixture omits), this line fails
// `tsc -b` — part of `npm run build` — rather than staying silent until a
// later task's component throws on an untyped field.
const _fixtureMatchesSchema: Loosen<DashboardDoc> = fixture;
void _fixtureMatchesSchema;

test("fixture is schema-complete at the top level", () => {
  expect(fixture.schema_version).toBe(1);
  expect(Object.keys(fixture.sections).length).toBeGreaterThan(0);
  expect(Object.keys(fixture.tickers).length).toBeGreaterThan(0);
  expect(Object.keys(fixture.glossary).length).toBeGreaterThan(0);
});

test("fixture covers a scorecard row with sparkline history", () => {
  const rows = fixture.sections.scorecard.rows ?? [];
  const withHistory = rows.find(
    (r) => Array.isArray(r.history) && r.history.length > 0,
  );
  expect(withHistory).toBeDefined();
});

// Belongs alongside the schema-drift guard above: the Loosen<T> check can't
// catch a live kicker value disagreeing with the Kicker union (JSON always
// reads back as plain `string`), so this asserts it at runtime instead —
// the guard Main.tsx's strand grouping relies on staying meaningful.
test("every section's kicker is a known strand", () => {
  for (const [id, sec] of Object.entries(fixture.sections)) {
    expect(KICKERS, `section "${id}" has kicker ${JSON.stringify(sec.kicker)}`).toContain(sec.kicker);
  }
});
