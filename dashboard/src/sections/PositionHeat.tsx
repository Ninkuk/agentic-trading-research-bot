// Your book: per-position risk contribution — the detail behind the book
// and group heat totals. sectionCell formats the dollar/percent columns the
// same way TickerDetail's position card does.

import type { Glossary, Section } from "../types";
import { sectionCell } from "../ui/sectionCells";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function PositionHeat({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="position-heat"
      glossary={glossary}
      renderCell={sectionCell}
    />
  );
}
