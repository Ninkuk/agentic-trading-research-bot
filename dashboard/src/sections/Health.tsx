// Ops strand: pipeline health — the layers the retired nightly ntfy push
// carried (exit codes, hung jobs, log marker counts, stale DBs). Rows are
// structured findings only; raw log lines never reach this document.
//
// Unlike other sections, the tiles must stay visible on a healthy night —
// "runs (24h)" and "jobs loaded" are the numbers worth seeing even when
// `rows` is empty, so `data.py`'s `_health` never sets `sec.empty` and
// SectionShell always hands this component its children instead of
// short-circuiting to the shell's own empty state (see SectionShell.tsx's
// `showEmpty`). This component owns its own all-clear line instead.

import type { Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { StatTile } from "../ui/StatTile";
import { formatCell } from "../ui/formatCell";

interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

function healthCell(row: Row, col: Column) {
  return formatCell(row[col.key]);
}

export function Health({ sec, glossary }: SectionComponentProps) {
  const rows = sec.rows ?? [];
  return (
    <>
      {sec.tiles && sec.tiles.length > 0 && (
        <div className="tiles">
          {sec.tiles.map((tile) => (
            <StatTile key={tile.label} tile={tile} />
          ))}
        </div>
      )}
      {rows.length > 0 ? (
        <DataTable
          columns={sec.columns ?? []}
          rows={rows}
          storageKey="health"
          glossary={glossary}
          renderCell={healthCell}
        />
      ) : (
        <p className="empty">All healthy — every job ran clean, every database is fresh.</p>
      )}
    </>
  );
}
