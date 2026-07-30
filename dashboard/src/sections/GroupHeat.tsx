// Your book: correlated positions collapsed into single bets (risk adds up
// within a group). Plain DataTable.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function GroupHeat({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="group-heat"
      glossary={glossary}
    />
  );
}
