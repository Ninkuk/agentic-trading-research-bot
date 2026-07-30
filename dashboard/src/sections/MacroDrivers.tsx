// The regime's three deciding inputs (10y-2y spread, high-yield spread,
// VIX), each a StatTile hosting a Sparkline of its own history plus the
// one-day delta. No up/down polarity applies to a raw macro level (a
// steeper curve or a calmer VIX isn't universally "good"), so every
// sparkline stays the neutral `hold` tone — color never claims a verdict
// these tiles don't make.

import { Sparkline } from "../charts/Sparkline";
import { signed } from "../format";
import type { Glossary, Section } from "../types";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Main.tsx always passes the section id (GenericSection needs it for a
  // stable storageKey); MacroDrivers doesn't need it, so it's unused here.
  id?: string;
}

export function MacroDrivers({ sec }: SectionComponentProps) {
  const tiles = sec.tiles ?? [];

  return (
    <div className="tiles">
      {tiles.map((tile) => (
        <StatTile key={tile.label} tile={tile}>
          {typeof tile.delta === "number" && <span className="d">{signed(tile.delta)}</span>}
          {tile.history && tile.history.length >= 2 && <Sparkline points={tile.history} tone="hold" />}
        </StatTile>
      ))}
    </div>
  );
}
