// Portfolio vs SPY (id "equity-curve"): the exporter's plain-English tiles
// ("Your picks" / "SPY" / "Cash") above the growth-of-$100 chart, with the
// ahead-or-behind verdict chip rendered by SectionShell in the header. The
// tiles are read straight off `sec.tiles`, never recomputed from `curve`,
// whose points are 2dp-rounded while the tiles derive from the unrounded
// indexes (data.py's `_equity_curve`). `curve_summary` keeps the raw
// fractions for cross-checking against the trader scorecard's text report.
//
// The `empty` (fewer than two trading days with a position) and `error`
// (missing DB) bodies omit `curve` entirely, and SectionShell renders both
// states before this component is reached — so an absent curve is a
// render-nothing case, not a state to duplicate here.

import { EquityCurve } from "../charts/EquityCurve";
import type { Glossary, Section } from "../types";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Main.tsx always passes the section id (GenericSection needs it for a
  // stable storageKey); this section doesn't, so it's unused here.
  id?: string;
}

export function PortfolioVsSpy({ sec }: SectionComponentProps) {
  if (!sec.curve || !sec.curve_summary) return null; // empty/error handled by SectionShell
  const s = sec.curve_summary;
  return (
    <div className="space-y-3">
      {sec.tiles && sec.tiles.length > 0 && (
        <div className="tiles">
          {sec.tiles.map((tile) => (
            <StatTile key={tile.label} tile={tile} />
          ))}
        </div>
      )}
      <EquityCurve
        rows={sec.curve}
        footnote={`${s.positions} positions · ${s.trading_days} trading days`}
      />
    </div>
  );
}
