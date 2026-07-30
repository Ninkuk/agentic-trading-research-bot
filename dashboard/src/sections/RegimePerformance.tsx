// Track record: does the regime call itself have forward edge — do risk-on
// nights actually precede better returns than risk-off nights? Plain
// DataTable.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function RegimePerformance({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="regime-performance"
      glossary={glossary}
    />
  );
}
