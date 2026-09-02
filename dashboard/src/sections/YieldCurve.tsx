// Treasury yield curve (id "yield-curve"): the maturity tiles ("3-month",
// "2-year", "10-year") become a line over maturity; every other tile (the
// spreads, with tone) stays a StatTile beside it. Under two numeric
// maturities there is no curve to draw, so tiles alone render.

import type { Glossary, Section, Tile } from "../types";
import { YieldCurveChart, type YieldCurvePoint } from "../charts/YieldCurveChart";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

const MATURITY = /^(\d+)-(month|year)$/;

function maturityPoint(tile: Tile): YieldCurvePoint | null {
  const m = MATURITY.exec(tile.label);
  if (!m || typeof tile.value !== "number") return null;
  const n = Number(m[1]);
  const months = m[2] === "year" ? n * 12 : n;
  return { label: `${n}${m[2] === "year" ? "y" : "m"}`, months, yield: tile.value };
}

export function YieldCurve({ sec }: SectionComponentProps) {
  const tiles = sec.tiles ?? [];
  const points = tiles.map(maturityPoint).filter((p): p is YieldCurvePoint => p !== null);
  const chart = points.length >= 2;
  const rest = chart ? tiles.filter((t) => maturityPoint(t) === null) : tiles;
  return (
    <div className="flex flex-wrap items-start gap-x-10 gap-y-4">
      {chart && (
        <div className="min-w-64 flex-1 basis-80">
          <YieldCurveChart points={points} />
        </div>
      )}
      {rest.length > 0 && (
        <div className="tiles">
          {rest.map((tile) => (
            <StatTile key={tile.label} tile={tile} />
          ))}
        </div>
      )}
    </div>
  );
}
