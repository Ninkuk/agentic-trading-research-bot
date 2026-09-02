// Ops: data-integrity checks — price moves that look like a split
// or a bad tick. An empty table is the GOOD outcome here (see the export's
// `empty` copy, rendered by SectionShell before this component mounts).
// Plain DataTable.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function BasisBreaks({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="basis-breaks"
      glossary={glossary}
    />
  );
}
