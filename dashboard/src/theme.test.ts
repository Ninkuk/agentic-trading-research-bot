import { tokens } from "./theme";

// Marks are CSS variable references since the 2026-07 shadcn redesign — the
// actual colors live in index.css (--tone-*) with light AND dark values, so
// a palette change is a CSS edit reviewed against both surfaces, never a
// silent JS tweak. This test pins the indirection itself: every mark token
// must resolve through a CSS variable (a raw hex here would render one
// fixed color across both themes).
test("mark tokens are theme-aware CSS variables", () => {
  for (const value of Object.values(tokens)) {
    expect(value).toMatch(/^var\(--[a-z-]+\)$/);
  }
});

test("up/down/hold map to the tone variables", () => {
  expect(tokens.up).toBe("var(--tone-up)");
  expect(tokens.down).toBe("var(--tone-down)");
  expect(tokens.hold).toBe("var(--tone-hold)");
});
