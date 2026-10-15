// Portfolio vs SPY (id "equity-curve"): the exporter's plain-English tiles
// ("Your picks" / "SPY" / "Cash") above the growth-of-$100 chart, with the
// ahead-or-behind verdict chip rendered by SectionShell in the header, and
// a Robinhood-style range row (1D … ALL) under the legend.
//
// On ALL the tiles, chip and footnote are the exporter's, never recomputed
// from `curve`: its points are 2dp-rounded while those derive from the
// unrounded indexes (data.py's `_equity_curve`). A narrower range has no
// exporter figure, so all three ARE computed from the window (curveWindow)
// — within a hundredth of a point of the truth, formatted like
// `_signed_pct` / `_book_verdict` so the two never look different. The
// chip sits in the shell's header, outside this component, so the window
// re-states it through SectionVerdictContext. Positions in the footnote
// is the book as held today, not a window quantity, so it never changes.
// `curve_summary` keeps the raw inception fractions for cross-checking
// against the trader scorecard's text report.
//
// The range is session state, not a pref: a reopened page should show ALL.
//
// The `empty` (fewer than two trading days with a position) and `error`
// (missing DB) bodies omit `curve` entirely, and SectionShell renders both
// states before this component is reached — so an absent curve is a
// render-nothing case, not a state to duplicate here.

import { useEffect, useState } from "react";
import {
  availableRanges,
  bookVerdict,
  CURVE_RANGES,
  windowCurve,
  type CurveRange,
  type CurveReturns,
} from "../charts/curveWindow";
import { EquityCurve } from "../charts/EquityCurve";
import { ToggleGroup, ToggleGroupItem } from "../components/ui/toggle-group";
import { signed } from "../format";
import type { Glossary, Section, Tile } from "../types";
import { useSetSectionVerdict } from "../ui/sectionVerdict";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Main.tsx always passes the section id (GenericSection needs it for a
  // stable storageKey); this section doesn't, so it's unused here.
  id?: string;
}

// Mirrors data.py's `_signed_pct`: "+8.62%", "−1.20%", "0.00%".
const pctTile = (label: string, v: number): Tile => ({
  label,
  value: `${signed(v * 100)}%`,
});

// The exporter ships a Cash tile only when DFF covers the window; so do we.
function windowTiles(r: CurveReturns): Tile[] {
  const tiles = [pctTile("Your picks", r.portfolio), pctTile("SPY", r.spy)];
  if (r.cash !== null) tiles.push(pctTile("Cash", r.cash));
  return tiles;
}

export function PortfolioVsSpy({ sec }: SectionComponentProps) {
  const [range, setRange] = useState<CurveRange>("ALL");
  const setVerdict = useSetSectionVerdict();
  const curve = sec.curve;
  const available = availableRanges(curve ?? []);
  const shown: CurveRange = available.has(range) ? range : "ALL";
  const win = windowCurve(curve ?? [], shown);
  const excess = win.returns.portfolio - win.returns.spy;
  useEffect(() => {
    setVerdict(shown === "ALL" || !curve ? null : bookVerdict(excess, win.since));
  }, [setVerdict, shown, curve, excess, win.since]);
  if (!curve || !sec.curve_summary) return null; // empty/error handled by SectionShell
  const s = sec.curve_summary;
  const tiles = shown === "ALL" ? (sec.tiles ?? []) : windowTiles(win.returns);
  const tradingDays = shown === "ALL" ? s.trading_days : win.tradingDays;

  return (
    <div className="space-y-3">
      {tiles.length > 0 && (
        <div className="tiles">
          {tiles.map((tile) => (
            <StatTile key={tile.label} tile={tile} />
          ))}
        </div>
      )}
      <EquityCurve
        rows={win.rows}
        footnote={`${s.positions} positions · ${tradingDays} trading days`}
        controls={
          // Single-select ToggleGroup: Radix renders the items as radios, so
          // the shown range is the checked one. An empty value is the group's
          // deselect, which a range has no meaning for — ignore it.
          <ToggleGroup
            type="single"
            size="sm"
            spacing={1}
            aria-label="Range"
            value={shown}
            onValueChange={(v) => {
              if (v) setRange(v as CurveRange);
            }}
          >
            {CURVE_RANGES.map((r) => (
              <ToggleGroupItem
                key={r}
                value={r}
                disabled={!available.has(r)}
                className="text-muted-foreground data-[state=on]:bg-primary data-[state=on]:text-primary-foreground rounded-full px-2.5 text-xs font-semibold"
              >
                {r}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        }
      />
    </div>
  );
}
