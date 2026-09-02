// Research: grades the candidates screen's list-entry TIMING only
// (21/63-day return vs. SPY, split by dislocation door) — never the
// multi-year quality thesis, and nothing here feeds back into the screen's
// gates. Plain DataTable; its `empty` state (rendered by SectionShell) is
// the expected view for the first ~21 trading days after the screen ships,
// not a failure.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function CandidateEfficacy({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="candidate-efficacy"
      glossary={glossary}
    />
  );
}
