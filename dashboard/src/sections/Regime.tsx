// The Macro strand's lead section: today's regime tiles (regime label, VIX,
// how many of the 11 inputs actually reported) plus the full drivers table
// (every input and which way it leaned) via DataTable. `data.py`'s `_regime`
// exporter emits `columns` alongside `rows` specifically so this renders
// through DataTable rather than a hand-rolled table.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { StatTile } from "../ui/StatTile";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Main.tsx always passes the section id (GenericSection needs it for a
  // stable storageKey); Regime doesn't need it, so it's unused here.
  id?: string;
}

export function Regime({ sec, glossary }: SectionComponentProps) {
  const tiles = sec.tiles ?? [];
  const columns = sec.columns ?? [];
  const rows = sec.rows ?? [];

  return (
    <>
      {tiles.length > 0 && (
        <div className="tiles">
          {tiles.map((tile) => (
            <StatTile key={tile.label} tile={tile} />
          ))}
        </div>
      )}
      {columns.length > 0 && (
        <DataTable columns={columns} rows={rows} storageKey="regime-drivers" glossary={glossary} />
      )}
    </>
  );
}
