// Track record (id "trader-scorecard"): the scorecard plain-text report
// (scorer/scorecard.py's `build_report`). Headline numbers parsed from the
// text lead as StatTiles; the six sub-tables (TextReport) sit under a
// session-only "Details" toggle — persisted expansion reopens as a wall.
// data.py's `_trader_scorecard` is `text_lines` only and has no `empty`
// state; TextReport falls back to <pre> if the format drifts.

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "../components/ui/button";
import type { Glossary, Section, Tile, Tone } from "../types";
import { StatTile } from "../ui/StatTile";
import { TextReport } from "../ui/TextReport";
import { parseScorecardHeadline, type ScorecardHeadline } from "../ui/scorecardHeadline";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

const signedPct = (v: number, dp = 2) => `${v > 0 ? "+" : ""}${v.toFixed(dp)}%`;
const signTone = (v: number): Tone | null => (v > 0 ? "on" : v < 0 ? "off" : null);

function headlineTiles(h: ScorecardHeadline): Tile[] {
  const tiles: Tile[] = [];
  if (h.twr) {
    const tone = signTone(h.twr.excess);
    tiles.push(
      { label: "portfolio TWR", value: `${h.twr.portfolio.toFixed(2)}%`, band: "inception", tone },
      { label: "SPY", value: `${h.twr.spy.toFixed(2)}%`, band: "inception", tone: null },
      { label: "excess", value: signedPct(h.twr.excess), band: "inception", tone },
    );
  }
  if (h.filterEdge) {
    tiles.push({
      label: "best pass edge",
      value: signedPct(h.filterEdge.excess * 100, 1),
      band: `${h.filterEdge.horizon}d · passed_inferred`,
      tone: signTone(h.filterEdge.excess),
    });
  }
  if (h.slippage !== null) {
    tiles.push({ label: "entry slippage", value: signedPct(h.slippage), band: "avg", tone: null });
  }
  if (h.alignment) {
    tiles.push({
      label: "agreed / contrarian",
      value: `${h.alignment.agreed} / ${h.alignment.contrarian}`,
      band: `${h.alignment.horizon}d`,
      tone: null,
    });
  }
  return tiles;
}

export function TraderScorecard({ sec }: SectionComponentProps) {
  const lines = sec.text_lines ?? [];
  const [open, setOpen] = useState(false);
  const headline = parseScorecardHeadline(lines);
  if (!headline) return <TextReport lines={lines} />;

  return (
    <div className="space-y-4">
      <div className="tiles">
        {headlineTiles(headline).map((tile) => (
          <StatTile key={tile.label} tile={tile} />
        ))}
      </div>
      <Button
        variant="ghost"
        size="sm"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown /> : <ChevronRight />}
        Details
      </Button>
      {open && <TextReport lines={lines} />}
    </div>
  );
}
