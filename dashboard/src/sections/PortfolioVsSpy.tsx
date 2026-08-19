// Portfolio vs SPY (id "equity-curve"): summary stats above the
// growth-of-$100 chart. The summary repeats the trader scorecard's
// inception numbers so chart and text report can be cross-checked at a
// glance — and it is read straight off `curve_summary`, never recomputed
// from `curve`, whose points are 2dp-rounded while the summary derives from
// the unrounded indexes (data.py's `_equity_curve`).
//
// The `empty` (fewer than two SPY-measurable dates) and `error` (orphan
// transfer) bodies omit `curve` entirely, and SectionShell renders both
// states before this component is reached — so an absent curve is a
// render-nothing case, not a state to duplicate here.

import { EquityCurve } from "../charts/EquityCurve";
import type { Glossary, Section } from "../types";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Main.tsx always passes the section id (GenericSection needs it for a
  // stable storageKey); this section doesn't, so it's unused here.
  id?: string;
}

const pct = (v: number) => `${(v * 100).toFixed(2)}%`;

export function PortfolioVsSpy({ sec }: SectionComponentProps) {
  if (!sec.curve || !sec.curve_summary) return null; // empty/error handled by SectionShell
  const s = sec.curve_summary;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-sm tabular-nums">
        <span>TWR {pct(s.twr)}</span>
        <span>SPY {pct(s.spy)}</span>
        <span>excess {pct(s.excess)}</span>
        {s.cash != null && <span>cash {pct(s.cash)}</span>}
        <span className="text-muted-foreground">
          {s.ledger_dates} ledger dates · {s.missing_trading_days} missing
        </span>
      </div>
      <EquityCurve rows={sec.curve} />
    </div>
  );
}
