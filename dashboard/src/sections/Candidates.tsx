// Research candidates: the quality-first screen (stocks.db via
// candidates.screen()) annotated from scorer.db with the ownership call
// research-ticker recorded and the current on-list tenure — a "pass" row is
// the screen-vs-research disagreement set. Columns come from the export, so
// this is a bare DataTable; SectionShell already renders `sec.error`/
// `sec.empty` before this component ever mounts.

import type { Glossary, Section } from "../types";
import { DataTable } from "../ui/DataTable";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function Candidates({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="candidates"
      glossary={glossary}
    />
  );
}
