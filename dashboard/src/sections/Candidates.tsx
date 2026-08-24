// Research candidates: the quality-first screen (stocks.db via
// candidates.screen()) annotated from scorer.db with the ownership call
// research-ticker recorded and the current on-list tenure — a "pass" row is
// the screen-vs-research disagreement set. Columns come from the export, so
// this is a bare DataTable; SectionShell already renders `sec.error`/
// `sec.empty` before this component ever mounts.

import type { ReactNode } from "react";
import type { Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { sectionCell } from "../ui/sectionCells";

// The list is the funnel's front door, so the symbol is the way into the
// ticker page — without it a candidate that composite never flagged had
// no route to its screen row and thesis.
function renderCandidateCell(row: Row, col: Column): ReactNode {
  if (col.key === "symbol") {
    const symbol = String(row.symbol ?? "");
    return (
      <a className="sym" href={`#/ticker/${symbol}`}>
        {symbol}
      </a>
    );
  }
  return sectionCell(row, col);
}

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
      renderCell={renderCandidateCell}
    />
  );
}
