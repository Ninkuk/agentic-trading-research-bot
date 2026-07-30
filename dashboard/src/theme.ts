// CVD-validated palette (aqua-green/red diverging, neutral-gray midpoint)
// against the #151a1e surface, validated 2026-07-28 with the dataviz
// palette validator (see the 2026-07-28 charts spec). `hold` is a deliberate
// alias of `muted` — the neutral midpoint, never brass. `brass` is accent
// ink only (kickers, links, focus rings) and must never be used as a data
// mark (up/down/hold).
export const tokens = {
  up: "#199e70",
  down: "#e66767",
  hold: "#9aa1ab",
  brass: "#e0bd76",
  brassDim: "#b39758",
  ink: "#0d1013",
  paper: "#151a1e",
  gutter: "#10161a",
  edge: "#232c33",
  fg: "#e8e6df",
  muted: "#9aa1ab",
  faint: "#7b828c",
} as const;

export type ThemeTokens = typeof tokens;
