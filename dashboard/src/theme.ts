// Chart-mark tokens as CSS variable references — SVG stroke/fill accept
// var(), so Recharts marks follow the active light/dark theme without any
// JS theme plumbing. The values live in index.css (`--tone-*`, shadcn
// tokens): Robinhood green/red-orange, stepped darker on light for AA text.
// `hold` is the amber midpoint; text remains the primary channel (color is
// never the only signal).
export const tokens = {
  up: "var(--tone-up)",
  down: "var(--tone-down)",
  hold: "var(--tone-hold)",
  // Accent ink (RegimeTimeline's brush). The brass hue itself is retired —
  // accent now follows the theme's primary.
  brass: "var(--primary)",
  ink: "var(--background)",
  paper: "var(--card)",
  gutter: "var(--muted)",
  edge: "var(--border)",
  fg: "var(--foreground)",
  muted: "var(--muted-foreground)",
  faint: "var(--muted-foreground)",
} as const;

export type ThemeTokens = typeof tokens;
