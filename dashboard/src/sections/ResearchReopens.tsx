// Research strand: open revisit triggers from research/verdicts.log.
// `renderCell` turns the "ticker" column into a link to the committed
// thesis doc — REPO_URL + "/blob/main/" + thesis_path — falling back to
// plain text when `thesis_path` is null (data.py's `_thesis_path` returns
// None when the ticker/date don't look like a real filename; never trust a
// free-text log column into a URL join without that guard already having
// run server-side).

import { type ReactNode } from "react";
import { REPO_URL } from "../constants";
import type { Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { formatCell } from "../ui/formatCell";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

function renderReopensCell(row: Row, col: Column): ReactNode {
  if (col.key === "ticker") {
    const symbol = String(row.ticker ?? "");
    const thesisPath = typeof row.thesis_path === "string" ? row.thesis_path : null;
    if (!thesisPath) return symbol;
    return (
      <a href={`${REPO_URL}/blob/main/${thesisPath}`} target="_blank" rel="noreferrer">
        {symbol}
      </a>
    );
  }
  return formatCell(row[col.key]);
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
