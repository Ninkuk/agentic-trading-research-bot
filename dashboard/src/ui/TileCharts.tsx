// Tiles that carry history render as small multiples that own the card:
// one column per tile (up to four; six grain tiles wrap as two rows of
// three), the headline value and band above a DriverChart. A wrapping
// tile row left the right half of the card empty while 90 daily points
// squeezed into a 96px sparkline. Tiles without history (the SOFR–IORB
// gap) keep their place in the grid, just shorter.

import { DriverChart } from "../charts/DriverChart";
import type { Tile } from "../types";
import { StatTile } from "./StatTile";
import { hasChart } from "./tileHistory";

const COLS: Record<number, string> = {
  1: "md:grid-cols-1",
  2: "md:grid-cols-2",
  3: "md:grid-cols-3",
  4: "md:grid-cols-4",
};

export function TileCharts({ tiles }: { tiles: Tile[] }) {
  const cols = COLS[tiles.length] ?? "md:grid-cols-3";
  return (
    <div className={`tile-charts grid gap-x-6 gap-y-8 ${cols}`}>
      {tiles.map((tile) => (
        <StatTile key={tile.label} tile={tile}>
          {hasChart(tile) && (
            <DriverChart label={tile.label} points={tile.history ?? []} thresholds={tile.thresholds} />
          )}
        </StatTile>
      ))}
    </div>
  );
}
