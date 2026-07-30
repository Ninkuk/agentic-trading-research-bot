// Track record (id "plan-001-report"): the verdict on each signal, graded
// against its own base rate. Plain DataTable — `recommendation` renders as
// plain text here (unlike SignalEfficacy's pill treatment on the same
// column name); the section's own verdict chip (keep/watch/anti-signal
// tally) already carries the at-a-glance read, via SectionShell.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function SignalRecommendations({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="plan-001-report"
      glossary={glossary}
    />
  );
}
