// Whether a tile's history is long enough to chart (DESIGN_MEMORY: no tiny
// 2-point sparklines). Kept out of TileCharts.tsx so that file exports
// only components (fast refresh).

import type { Tile } from "../types";

export const MIN_POINTS = 3;

export function hasChart(tile: Tile): boolean {
  return (tile.history?.filter((p) => p.value !== null).length ?? 0) >= MIN_POINTS;
}
