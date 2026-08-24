// Research strand: open revisit triggers from research/verdicts.log.
// `renderCell` turns the "ticker" column into a link to the ticker page
// (#/ticker/SYM) — every researched symbol has one, and the newest thesis
// renders there inline with its own GitHub link for the history.

import { type ReactNode } from "react";
import type { Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { sectionCell } from "../ui/sectionCells";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

function renderReopensCell(row: Row, col: Column): ReactNode {
  if (col.key === "ticker") {
    const symbol = String(row.ticker ?? "");
    return (
      <a className="sym" href={`#/ticker/${symbol}`}>
        {symbol}
      </a>
    );
  }
  // Everything else through the shared heuristics: verdict pills
  // (SOUND/FLAWED/UNPROVEN tones) and humanized trigger slugs included.
  return sectionCell(row, col);
}

function whenLabel(days: number): string {
  if (days === 0) return "today";
  return days > 0 ? `in ${days}d` : `${-days}d ago`;
}

export function ResearchReopens({ sec, glossary }: SectionComponentProps) {
  const checkpoints = sec.checkpoints ?? [];
  return (
    <>
      {checkpoints.length > 0 && (
        <ul className="verdict-list">
          {checkpoints.map((c) => (
            <li key={`${c.ticker}-${c.reopen_date}`}>
              <strong>{c.ticker}</strong> — held position checkpoint: {c.trigger} ·{" "}
              {c.reopen_date} ({whenLabel(c.when_days)})
            </li>
          ))}
        </ul>
      )}
      <DataTable
        columns={sec.columns ?? []}
        rows={sec.rows ?? []}
        storageKey="research-reopens"
        glossary={glossary}
        renderCell={renderReopensCell}
      />
    </>
  );
}
