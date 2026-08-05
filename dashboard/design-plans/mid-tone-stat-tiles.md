# Render tone="mid" stat-tile values in the amber tone token, not muted gray

Written against: 805489c

## Evidence chain

- Surface: `dashboard/src/ui/StatTile.tsx` rendering tiles on the Main route
  (`src/routes/Main.tsx` → `Regime.tsx:29`, `BookHeat.tsx:22`, and
  `GenericSection`'s tiles path).
- Problem: `TONE_CLASS` (`StatTile.tsx:14-18`) maps `mid → "tag-dim"`, and
  `.tag-dim` is `color: var(--muted-foreground)` (`index.css:207-209`) — so a
  mid-tone stat value renders muted gray. Tonight's live `regime` tile
  (`public/data.json`: `value: "mixed", tone: "mid"`) shows this.
- Design evidence: `dashboard/DESIGN_MEMORY.md:13` — "Tones: on/off/mid →
  emerald/red/amber". Every sibling `mid` surface on the same page follows it:
  the hero bullet dot (`Main.tsx:74-78`, `mid: "var(--tone-hold)"`, amber) and
  the verdict badge (`components/ui/badge.tsx:19`, `hold` variant, amber).
  StatTile is the one consumer of the Tone type that renders `mid` gray.
- Owner: `--tone-hold` token (`src/index.css:76` light, `:108` dark), already
  documented at `index.css:70-73` as the data-mark tone set chosen for AA
  contrast on both surfaces.
- Scope and affected surfaces: `regime` tiles (live tonight), `book-heat`
  tiles, and any future tile the exporter marks `tone: "mid"`.
- Uncertainty: none.

## Design decision

Map `mid` to the amber tone token so all four tone consumers (dot, badge,
chart marks, stat tiles) agree with the documented mapping. Text remains the
primary channel (the value string "mixed" still carries the meaning); this
only aligns the color channel with its siblings.

## Reuse

- `var(--tone-hold)` — the existing amber data-mark token, both themes.
- Exemplar: `.tag-on` / `.tag-off` (`src/index.css:201-206`) — identical
  one-line color classes on the sibling tokens.

No new primitive: the token exists; only the class mapping is missing.

## Changes

1. `dashboard/src/index.css`
   - Change: next to `.tag-on`/`.tag-off` (lines 201-206), add
     `.tag-hold { color: var(--tone-hold); }` and delete the now-orphaned
     `.tag-dim` rule (lines 207-209 — its only consumer is the mapping
     changed below; verified via repo-wide grep at 805489c).
   - Preserve: `.tag-on`/`.tag-off` untouched.
   - Verify: `grep -rn "tag-dim" dashboard/src` returns nothing.
2. `dashboard/src/ui/StatTile.tsx`
   - Change: `TONE_CLASS` line 17 from `mid: "tag-dim"` to `mid: "tag-hold"`.
   - Preserve: `on`/`off` mappings, value/caption formatting, the equity
     `usd()` special case, the children sparkline slot.
   - Verify: rendering `<StatTile tile={{ label: "regime", value: "mixed", tone: "mid" }} />`
     puts class `tag-hold` on the `.v` element.
3. `dashboard/src/ui/StatTile.test.tsx`
   - Change: add a test asserting the `mid` tone renders with class
     `tag-hold` (none of the existing six tests pins tone classes).
   - Preserve: existing tests unchanged.
   - Verify: `cd dashboard && npx vitest run src/ui/StatTile.test.tsx` passes.

## Scope

- Inherit: all `StatTile` consumers — `Regime`, `BookHeat`, `GenericSection`
  tiles path (`routes/Main.tsx:136-144`), `PositionCard` uses no tones.
- Verify: the `regime` section card in the Macro strand shows "mixed" in
  amber; `book-heat` tiles unchanged unless they carry `tone: "mid"`.
- Exclude: the hero KPI row in `Main.tsx` (renders macro tiles inline by the
  accepted lab anatomy, no tone field); `RegimeTimeline` dot hexes (its
  comment records the fixed palette as deliberate); Badge variants.

## Validation

- Product: open the dashboard, Macro strand — the regime tile value "mixed"
  reads amber, matching the hero dot and the "Regime: mixed" badge above it.
- Interface: check both themes (toggle in the masthead): light amber-600
  `#d97706`, dark amber-400 `#fbbf24`; also a tile with `tone: "on"` and one
  with no tone to confirm they are unaffected.
- System: confirm no second `mid`-tone color mapping remains
  (`grep -rn "tag-dim\|tone-hold" dashboard/src`).
- Repository: `cd dashboard && npx vitest run && npx oxlint src` → all pass.

## Stop conditions

- Stop if any consumer of `.tag-dim` besides `StatTile.tsx:17` exists at the
  executor's commit, or if `--tone-hold` has been removed/renamed.

## Design documentation

- After acceptance and validation: none — this brings the code into
  conformance with the already-recorded rule in `DESIGN_MEMORY.md:13`.
