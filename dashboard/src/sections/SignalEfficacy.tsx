// Track record: every signal's raw report card — how often it has been
// right, against the base rate it would need to beat to be worth anything.
// The lab treatment: the CI columns fold INTO the hit-rate cell (a muted
// "CI 49–67" stacked under "58%") instead of sitting beside it as three
// raw-fraction columns, and the keep/watch/anti-signal verdict renders as
// a tinted pill (text is always the primary channel — color never carries
// meaning alone). Column dropping + per-key formatting both come from
// ui/sectionCells.tsx so this table and plan-001's stay in lockstep.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { sectionCell, visibleColumns } from "../ui/sectionCells";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function SignalEfficacy({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={visibleColumns(sec.columns ?? [])}
      rows={sec.rows ?? []}
      storageKey="signal-efficacy"
      glossary={glossary}
      renderCell={sectionCell}
    />
  );
}
