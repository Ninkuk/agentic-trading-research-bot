// Ops: opinions already recorded whose outcome hasn't matured yet.
// `sec.total` is COUNT(*) over the full live view (~47K rows); `sec.rows` is
// a LIMIT-100 port of it — the "showing N of TOTAL" line is the disclosure
// the legacy `.cap` note made, so it must render even though DataTable's own
// row count (visible/expanded) is a different, smaller number.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function Pending({ sec, glossary }: SectionComponentProps) {
  const rows = sec.rows ?? [];
  return (
    <>
      {typeof sec.total === "number" && (
        <p className="cap">
          showing {rows.length} of {sec.total}
        </p>
      )}
      <DataTable columns={sec.columns ?? []} rows={rows} storageKey="pending" glossary={glossary} />
    </>
  );
}
