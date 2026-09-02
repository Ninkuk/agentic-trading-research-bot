// oxlint-disable react/only-export-components -- verdictCounts/dueSoonCount
// are exported for tests; the one component here still fast-refreshes.
//
// Research strand: open revisit triggers from research/verdicts.log.
// Summary first (KPI tiles, verdict mix), table second. `today` is
// injected for the due-soon tile, defaulting to the rows' earliest due
// date so the fixture renders the same on every run. `renderCell` turns
// the "ticker" column into a link to the ticker page (#/ticker/SYM) —
// every researched symbol has one.

import type { ReactNode } from "react";
import type { Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { sectionCell } from "../ui/sectionCells";
import { VerdictMix, type VerdictCounts } from "../charts/VerdictMix";

const DAY_MS = 86_400_000;

function parseDate(s: string): number | null {
  const t = Date.parse(s);
  return Number.isNaN(t) ? null : t;
}

/** Day offset of `due` from `today`, or null when either is not a date. */
export function dayOffset(today: string, due: string): number | null {
  const a = parseDate(today);
  const b = parseDate(due);
  if (a === null || b === null) return null;
  return Math.round((b - a) / DAY_MS);
}

/** Earliest due date across rows — the deterministic fixture "today". */
export function defaultToday(rows: Row[]): string | null {
  const dues = rows
    .map((r) => (typeof r.due === "string" ? r.due : null))
    .filter((d): d is string => d !== null && parseDate(d) !== null)
    .sort();
  return dues[0] ?? null;
}

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
  today?: string;
}

const DUE_SOON_DAYS = 7;

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

export function verdictCounts(rows: Row[]): VerdictCounts {
  const counts: VerdictCounts = { SOUND: 0, UNPROVEN: 0, FLAWED: 0 };
  for (const r of rows) {
    const v = typeof r.verdict === "string" ? r.verdict.toUpperCase() : "";
    if (v in counts) counts[v as keyof VerdictCounts] += 1;
  }
  return counts;
}

/** Rows due within [today, today + 7d]; past-due rows are not "soon". */
export function dueSoonCount(rows: Row[], today: string | null): number {
  if (today === null) return 0;
  return rows.filter((r) => {
    if (typeof r.due !== "string") return false;
    const d = dayOffset(today, r.due);
    return d !== null && d >= 0 && d <= DUE_SOON_DAYS;
  }).length;
}

function Kpi({ value, label }: { value: number; label: string }) {
  return (
    <div className="tile">
      <div className="v">{value}</div>
      <div className="k">{label}</div>
    </div>
  );
}

export function ResearchReopens({ sec, glossary, today: todayProp }: SectionComponentProps) {
  const checkpoints = sec.checkpoints ?? [];
  const rows = sec.rows ?? [];
  const today = todayProp ?? defaultToday(rows);
  const held = rows.filter((r) => r.held === true).length;
  return (
    <>
      {rows.length > 0 && (
        <div className="research-summary mb-4 space-y-4">
          <div className="tiles">
            <Kpi value={rows.length} label="open theses" />
            <Kpi value={held} label="held" />
            <Kpi value={dueSoonCount(rows, today)} label={`due within ${DUE_SOON_DAYS} days`} />
          </div>
          <VerdictMix counts={verdictCounts(rows)} />
        </div>
      )}
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
        rows={rows}
        storageKey="research-reopens"
        glossary={glossary}
        renderCell={renderReopensCell}
      />
    </>
  );
}
