// Track record: acted-on vs. passed-on flags — did the human's judgment add
// edge over what the flag alone would have done? Plain DataTable.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function HumanFilter({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="human-filter"
      glossary={glossary}
    />
  );
}
