// Research candidates: a plain quality-first screen (stocks.db via
// candidates.screen()). No score/verdict of its own — see data.py's
// `_candidates` docstring — so this is a bare DataTable over the exported
// columns/rows; SectionShell already renders `sec.error`/`sec.empty` before
// this component ever mounts (a missing/broken stocks.db is the common
// live case).

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
