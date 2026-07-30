// Your book: a volatility-scaled position-size ceiling per flagged
// candidate — decision support only, never an order. sectionCell formats
// the dollar columns.

import type { Glossary, Section } from "../types";
import { sectionCell } from "../ui/sectionCells";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function SizeCaps({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="size-caps"
      glossary={glossary}
      renderCell={sectionCell}
    />
  );
}
