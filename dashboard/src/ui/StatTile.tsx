// A single readout: a big value with a small "label · band" caption below
// it (e.g. value 14.2, caption "VIX · calm"), plus an optional sparkline
// slot passed as children (macro-drivers tiles carry history for this).

import type { ReactNode } from "react";
import { num, signed, usd } from "../format";
import type { CellValue, Tile, Tone } from "../types";
import { humanizeId, isMachineId } from "./formatCell";

export interface StatTileProps {
  tile: Tile;
  children?: ReactNode;
}

const TONE_CLASS: Record<Tone, string> = {
  on: "tag-on",
  off: "tag-off",
  mid: "tag-hold",
};

function formatValue(value: CellValue | undefined): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? num(value, 0) : num(value);
  // A machine id as a tile headline ("risk_on") is the exporter's raw
  // value showing through — render it as words either way.
  return isMachineId(value) ? humanizeId(value) : value;
}

export function StatTile({ tile, children }: StatTileProps) {
  const toneClass = tile.tone ? TONE_CLASS[tile.tone] : undefined;
  const caption = tile.band ? `${tile.label} · ${tile.band}` : tile.label;
  // Equity is the one dollar-amount tile (lab spec: "$84,213.55", never a
  // bare float beside percent tiles).
  const display =
    tile.label === "equity" && typeof tile.value === "number"
      ? usd(tile.value)
      : formatValue(tile.value);

  return (
    <div className="tile">
      <div className={["v", toneClass].filter(Boolean).join(" ")}>
        {display}
        {typeof tile.delta === "number" && (
          <span className="text-muted-foreground ml-1.5 text-xs font-normal">
            {signed(tile.delta)}
          </span>
        )}
      </div>
      <div className="k">{caption}</div>
      {children}
    </div>
  );
}
