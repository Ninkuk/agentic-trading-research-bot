---
name: Trading Research Dashboard
description: Calm plain-English nightly signal dashboard on shadcn/zinc
colors:
  paper-white: "oklch(1 0 0)"
  ink-zinc: "oklch(0.141 0.005 285.823)"
  card-white: "oklch(1 0 0)"
  quiet-zinc: "oklch(0.967 0.001 286.375)"
  caption-zinc: "oklch(0.552 0.016 285.938)"
  hairline-zinc: "oklch(0.92 0.004 286.32)"
  alert-red: "oklch(0.577 0.245 27.325)"
  tone-up: "#047857"
  tone-down: "#b91c1c"
  tone-hold: "#d97706"
  tone-up-bg: "rgba(16, 185, 129, 0.14)"
  tone-down-bg: "rgba(239, 68, 68, 0.13)"
  tone-hold-bg: "rgba(245, 158, 11, 0.15)"
typography:
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.3
  stat:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.2
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
  numeric:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    fontFeature: "tabular-nums"
rounded:
  sm: "calc(0.625rem - 4px)"
  md: "calc(0.625rem - 2px)"
  lg: "0.625rem"
  xl: "calc(0.625rem + 4px)"
spacing:
  page-width: "72rem"
  page-pad-x: "1.25rem"
  page-pad-top: "1.5rem"
  tile-gap: "1rem 2.5rem"
  prose-measure: "75ch"
components:
  badge-up:
    backgroundColor: "{colors.tone-up-bg}"
    textColor: "{colors.tone-up}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  badge-down:
    backgroundColor: "{colors.tone-down-bg}"
    textColor: "{colors.tone-down}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  badge-hold:
    backgroundColor: "{colors.tone-hold-bg}"
    textColor: "{colors.tone-hold}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  section-card:
    backgroundColor: "{colors.card-white}"
    textColor: "{colors.ink-zinc}"
    rounded: "{rounded.xl}"
---

# Design System: Trading Research Dashboard

## 1. Overview

**Creative North Star: "The Plain-English Briefing"**

A nightly report you read, not a terminal you watch. The system is
shadcn/ui zinc on Tailwind v4: near-white paper, near-black ink, hairline
borders, comfortable density. Every visual element defers to a sentence of
plain English; color exists only to echo what the words already said. The
palette carries exactly three semantic tones (up, down, hold) and one
destructive red; everything else is tinted zinc neutral.

This system explicitly rejects its own predecessor: the newspaper-ledger
ornament (serif display, brass, margin gutters) was retired 2026-07-30 as
"too stylized, hard to read". It equally rejects the opposite pole,
trading-terminal maximalism. Both light and dark themes are first-class;
the OS chooses by default and a manual toggle overrides.

**Key Characteristics:**
- Borders over shadows; flat surfaces, hairline separation
- Text is the primary channel; tones reinforce, never replace
- Mono tabular numerals for every number, sans for every sentence
- One-sentence section notes; deep anatomy behind an About modal
- Honest degraded states (dashed `empty`, red mono `unavailable`)

## 2. Colors

Tinted zinc neutrals with three data tones: a Restrained strategy where
the accents are semantic, not decorative.

### Primary
- **Ink Zinc** (oklch(0.141 0.005 285.823)): body text, and inverted as
  the primary button surface. In dark mode the pair flips (near-white ink
  on zinc-9 paper). There is no brand accent color; the "primary" is ink.

### Neutral
- **Paper White** (oklch(1 0 0)): page and card background in light mode.
- **Quiet Zinc** (oklch(0.967 0.001 286.375)): secondary/muted/accent
  fills — hover states, muted table headers, tab strips.
- **Caption Zinc** (oklch(0.552 0.016 285.938)): captions, tile labels,
  section notes' de-emphasized metadata.
- **Hairline Zinc** (oklch(0.92 0.004 286.32)): every border, divider, and
  input stroke. Dark mode uses white at 10% alpha instead.

### Tertiary (data tones)
- **Tone Up** (#047857, emerald-700): positive/on states; dark mode
  brightens to emerald-400 (#34d399).
- **Tone Down** (#b91c1c, red-700): negative/off states; dark mode
  red-400 (#f87171).
- **Tone Hold** (#d97706, amber-600): neutral/hold states and flagged
  table rows; dark mode amber-400 (#fbbf24).
- Each tone has a soft ~14%-alpha background tint for badges and flagged
  rows.
- **Alert Red** (oklch(0.577 0.245 27.325)): destructive/unavailable
  states only; never a data tone.

### Named Rules
**The Words-First Rule.** Color never carries meaning alone. Every tone
badge has a text label; every flagged row also gets a ★ suffix. If
removing all color would lose information, the design is wrong.

**The Three-Tones Rule.** Up, down, hold — that is the entire semantic
palette. New signal states map into these three; never mint a fourth
color.

## 3. Typography

**Body Font:** system sans (ui-sans-serif → Segoe UI/Roboto)
**Numeric/Stat Font:** system mono (ui-monospace → SF Mono/Menlo/Consolas)

**Character:** Invisible, OS-native, deliberately unremarkable. The one
typographic opinion is the sans/mono split: sentences are sans, numbers
and ticker symbols are mono with tabular figures.

### Hierarchy
- **Stat** (600, 1.125rem mono, lh 1.2): stat-tile values.
- **Title** (600, 1.125rem, lh 1.3): card/section titles. A real step over
  body (1.29 ratio); at 1rem the page read as one flat size.
- **Read** (400, 1rem): the summary card's hero bullets, the lead reading
  block, one step over body.
- **Body** (400, 14px, lh 1.55): notes and prose; prose is capped at
  75ch measure even inside page-wide cards.
- **Numeric** (400, 0.8125rem mono, tabular-nums): table cells,
  right-aligned.
- **Label** (400, 0.75rem, caption zinc): tile captions, caveat
  footnotes (italic), tooltip text, column direction hints.

### Named Rules
**The Mono-Numbers Rule.** Every numeral the user might compare or scan —
tables, tiles, tooltips, ticker symbols — is mono with tabular-nums and
right-aligned in tables. Sans numerals are permitted only inside running
prose.

**The 12px Floor Rule.** No functional text below 0.75rem, ever, and
nothing below full `muted-foreground` contrast. A hint too small or too
faint to pass AA is a hint that doesn't exist.

## 4. Elevation

Flat, border-separated surfaces. Cards, tables, and tabs are delimited by
1px Hairline Zinc borders on same-color backgrounds; there are no resting
shadows anywhere. Shadows exist only on floating layers — tooltips and
popovers (`0 4px 12px` / `0 6px 18px` at ~15% black) — where they signal
"this is above the page", never importance.

### Named Rules
**The Floating-Only Rule.** A shadow means the element is temporally
floating (tooltip, popover, dialog). Nothing that rests in the page flow
casts one.

## 5. Components

### Section Cards
- **Corner Style:** rounded-xl (0.625rem + 4px, shadcn card default)
- **Background:** Card White (zinc-9 surface in dark), 1px hairline border
- **Shadow Strategy:** none (see Elevation)
- **Anatomy:** title + one-sentence note as description, verdict badge in
  the header action slot, info icon opening the About modal, optional
  italic bordered caveat footnote (`.cap`)

### Tone Badges (`Badge variant="up|down|hold"`)
- **Style:** soft ~14%-alpha tone background, solid tone text, small
  radius, text label always present
- **State:** static; badges are read-only verdicts, never interactive

### Stat Tiles
- **Style:** unboxed — mono 600 value over a 0.75rem caption-zinc label,
  flex-wrapped with 1rem × 2.5rem gaps. Not cards; no border.
- **Tone:** value may take a tone color via tag-on/off/hold classes

### Data Tables
- **Style:** sortable headers with persisted sort, filter box at ≥4 rows,
  numeric cells mono/tabular/right-aligned, flagged rows get Tone Hold
  tint plus ★ on the symbol
- **Rule:** confidence intervals stack under the hit-rate value in the
  same cell, never inline suffixes

### Charts & Sparklines
- **Style:** shadcn ChartContainer/ChartTooltip on Recharts; tooltips
  float above the chart in mono
- **Rule:** sparklines use a hidden auto-domain YAxis (zero-baseline turns
  them into filled boxes); a series under ~3 points renders no chart

### Glossary Terms
- **Style:** dotted underline, cursor: help, popover on hover/focus;
  the popover portals to `document.body` (fixed-positioned from the
  trigger rect) so table overflow containers can never clip it
- **Focus:** 2px ring outline, offset 2px, 2px corner radius (a
  deliberate micro-radius for text-level focus outlines; the rounded
  scale applies to boxes, not text outlines)

### Degraded States
- **Empty:** dashed hairline border, muted text ("no rows this run")
- **Unavailable:** red-tinted border/background, mono red error text

## 6. Do's and Don'ts

### Do:
- **Do** keep section notes to ONE sentence of meaning ("what is this and
  should I care"); move all widget anatomy to the About modal.
- **Do** read page width from `--page-width` (72rem) everywhere,
  including components outside `.page` like StaleBanner.
- **Do** cap prose at 75ch even when the card is page-wide.
- **Do** render partial data as `empty`/`unavailable` states; a missing
  section must say so.
- **Do** respect `prefers-reduced-motion` (global transition kill).

### Don't:
- **Don't** revive newspaper ornament: no serif display, no brass
  accents, no margin gutters. Retired 2026-07-30, "too stylized, hard to
  read".
- **Don't** build trading-terminal maximalism: no dense blinking grids,
  no neon-on-black, no data density as identity.
- **Don't** put counts in tab labels (user preference, 2026-07-30).
- **Don't** ship 2-point sparklines or zero-baseline sparkline domains.
- **Don't** use color as the only signal; every tone needs a text twin.
- **Don't** add resting shadows, side-stripe borders, or gradient text;
  separation is a 1px hairline, emphasis is weight.
