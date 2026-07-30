// Your book's lead section: book-wide risk-at-risk tiles (positions, heat
// %, coverage, equity, sources failed). Mirrors Regime's tile block — the
// band label (e.g. "comfortable"/"elevated") already rides on `tile.band`
// via StatTile, nothing extra to inject here. `sec.tiles` is `[]` and
// `sec.empty` is set when no advisor snapshot exists yet; SectionShell
// renders that empty note before this component ever mounts.

import type { Glossary, Section } from "../types";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function BookHeat({ sec }: SectionComponentProps) {
  const tiles = sec.tiles ?? [];
  return (
    <div className="tiles">
      {tiles.map((tile) => (
        <StatTile key={tile.label} tile={tile} />
      ))}
    </div>
  );
}
