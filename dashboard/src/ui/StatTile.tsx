// A single readout: a big value with a small "label · band" caption below
// it (e.g. value 14.2, caption "VIX · calm"), plus an optional sparkline
// slot passed as children (macro-drivers tiles carry history for this).

import type { ReactNode } from "react";
import { num } from "../format";
import type { CellValue, Tile, Tone } from "../types";

export interface StatTileProps {
  tile: Tile;
  children?: ReactNode;
}

const TONE_CLASS: Record<Tone, string> = {
  on: "tag-on",
  off: "tag-off",
  mid: "tag-dim",
};

function formatValue(value: CellValue | undefined): string {
  if (value === undefined || value === null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? num(value, 0) : num(value);
  return value;
}

export function StatTile({ tile, children }: StatTileProps) {
  const toneClass = tile.tone ? TONE_CLASS[tile.tone] : undefined;
  const caption = tile.band ? `${tile.label} · ${tile.band}` : tile.label;

  return (
    <div className="tile">
      <div className={["v", toneClass].filter(Boolean).join(" ")}>{formatValue(tile.value)}</div>
      <div className="k">{caption}</div>
      {children}
    </div>
  );
}
