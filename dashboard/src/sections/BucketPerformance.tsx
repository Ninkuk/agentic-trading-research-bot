// Signals: past opinions grouped by conviction bucket, graded against
// SPY. Plain DataTable — every column's up-good/down-good arrow already
// comes from the export (data.py's `_track_col`), nothing to inject here.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function BucketPerformance({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="bucket-performance"
      glossary={glossary}
    />
  );
}
