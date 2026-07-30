import { tokens } from "./theme";

// These hexes were validated with the dataviz palette validator against the
// #151a1e surface on 2026-07-28 (see the 2026-07-28 charts spec). A "tweak"
// that changes them must re-run validation — this test makes that deliberate.
test("validated palette is intact", () => {
  expect(tokens.up).toBe("#199e70");
  expect(tokens.down).toBe("#e66767");
  expect(tokens.brass).toBe("#e0bd76");
  expect(tokens.paper).toBe("#151a1e");
});

test("hold midpoint is neutral, not brass", () => {
  expect(tokens.hold).toBe(tokens.muted); // gray midpoint — brass is ink, not a mark
});
