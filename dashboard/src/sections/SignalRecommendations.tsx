// Track record (id "signal-recommendations"): the verdict on each signal, graded
// against its own base rate. Same lab treatment as Signal efficacy — CI
// columns fold into the stacked hit-rate cell, recommendation renders as a
// tinted pill, signed excess as a tinted percent — all via the shared
// heuristics in ui/sectionCells.tsx, so the two signal report cards never
// disagree about how the same quantities read.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { sectionCell, visibleColumns } from "../ui/sectionCells";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function SignalRecommendations({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={visibleColumns(sec.columns ?? [])}
      rows={sec.rows ?? []}
      storageKey="signal-recommendations"
      glossary={glossary}
      renderCell={sectionCell}
    />
  );
}
