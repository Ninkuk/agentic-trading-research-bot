# Product

## Register

product

## Users

One person: the repo owner, a solo retail investor who is deliberately
beginner-friendly in framing. They open the dashboard once a day (usually
evening, Phoenix time) to read the nightly signal report — market regime,
per-ticker scorecard, book heat, decision-journal grades — and decide
whether anything deserves attention. They are not a professional trader
staring at this all day; the job is a calm daily read, not real-time
monitoring.

## Product Purpose

A static React dashboard rendering `reports/data.json`, the nightly output
of ~20 official-source screeners and combiners. It exists to make the
signal layer legible to a human: every section answers "what is this and
should I care" in plain English before showing numbers. Success is the
user understanding their book and the market regime in a five-minute read,
with zero mystery widgets. It is decision support only — nothing here
places orders.

## Brand Personality

Calm, practical, plain-English. Explanations are a feature, not chrome:
every section keeps its one-sentence note, every stat its caption, every
metric a glossary term popover. The voice is a patient explainer, never a
Bloomberg terminal flexing density.

## Anti-references

- Newspaper ornament: serif display, brass accents, margin gutters.
  Retired 2026-07-30 after "too stylized, hard to read" feedback. Never
  bring it back.
- Trading-terminal maximalism: dense grids of blinking numbers, dark-only
  neon, data density as identity.
- Widget-anatomy walls of text: section notes explain meaning, never
  mechanics (anatomy lives in the per-section About modal).

## Design Principles

- Plain English first: text is always the primary channel; color and
  ornament only reinforce what words already say.
- One sentence of meaning per section: the note says what it is and
  whether to care; everything deeper goes behind the About modal.
- Calm over dense: comfortable density, borders over shadows, restrained
  neutrals with semantic tones (up/down/hold) as the only color.
- Degrade honestly: partial data renders as labelled empty/unavailable
  states, never blank space or fake zeros.
- Numbers behave like numbers: mono, tabular-nums, right-aligned,
  sortable.

## Accessibility & Inclusion

No formal WCAG target recorded. Existing commitments to preserve:
system-default light/dark with manual toggle, `prefers-reduced-motion`
respected globally, color never the only signal (tone badges always carry
text), focus-visible outlines on interactive glossary terms.
