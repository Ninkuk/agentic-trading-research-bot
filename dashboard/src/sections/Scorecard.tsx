// Signals strand flagship: every scored ticker's net vote. `renderCell`
// injects the diverging ScoreBar into the "score_sum" column, plus a trend
// Sparkline underneath when the row carries score history (only headline
// symbols get one — data.py's `_SCORECARD_HISTORY_LIMIT` — a bare
// `number[]` of past score_sums, not the {date,value} shape Sparkline
// wants, so index-position stands in for a date here). The "symbol" column
// becomes a link to the ticker drill-down. Flagged rows keep the ★ +
// brass left-edge treatment via DataTable's `rowClassName` hook, which
// applies the "flag" class the static page's CSS already understands
// (tr.flag / tr.flag .sym::after in index.css) — no extra JSX marker
// needed. The ticker filter reuses the legacy `#tickfilter` id and its
// styling, persisted via usePrefs so a filter typed tonight survives a
// reload. `pinnedFirst` reads the same `usePrefs("pins", [])` list
// TickerDetail's pin toggle writes — a ticker pinned from its drill-down
// page groups above the rest here too, active sort still applying within
// each group (DataTable's own pinnedFirst grouping).

import { type ReactNode } from "react";
import { Sparkline, type SparklinePoint } from "../charts/Sparkline";
import { ScoreBar } from "../charts/ScoreBar";
import { usePrefs } from "../hooks/usePrefs";
import type { CellValue, Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { formatCell } from "../ui/formatCell";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

// Mirrors sections.py's `_SCORE_BAR_MAX` — the bar's fixed comparison cap
// (not per-row 2*total), so bars stay comparable down the column.
const SCORE_BAR_MAX = 5;

function toSparklinePoints(history: CellValue | undefined): SparklinePoint[] {
  if (!Array.isArray(history)) return [];
  return history.map((value, i) => ({
    date: String(i),
    value: typeof value === "number" ? value : null,
  }));
}

function renderScorecardCell(row: Row, col: Column): ReactNode {
  if (col.key === "symbol") {
    const symbol = String(row.symbol ?? "");
    return (
      <a className="sym" href={`#/ticker/${symbol}`}>
        {symbol}
      </a>
    );
  }
  if (col.key === "score_sum") {
    const value = typeof row.score_sum === "number" ? row.score_sum : 0;
    const bullish = typeof row.bullish === "number" ? row.bullish : 0;
    const bearish = typeof row.bearish === "number" ? row.bearish : 0;
    const points = toSparklinePoints(row.history);
    return (
      <>
        <ScoreBar value={value} bullish={bullish} bearish={bearish} max={SCORE_BAR_MAX} />
        {points.length >= 2 && <Sparkline points={points} tone="hold" />}
      </>
    );
  }
  return formatCell(row[col.key]);
}

export function Scorecard({ sec, glossary }: SectionComponentProps) {
  const [filter, setFilter] = usePrefs("scorecard:filter", "");
  const [pins] = usePrefs<string[]>("pins", []);
  const columns = sec.columns ?? [];
  const allRows = sec.rows ?? [];
  const needle = filter.trim().toUpperCase();
  const rows = needle
    ? allRows.filter((r) => typeof r.symbol === "string" && r.symbol.toUpperCase().includes(needle))
    : allRows;

  return (
    <>
      <input
        id="tickfilter"
        type="search"
        placeholder="filter tickers"
        aria-label="filter tickers"
        value={filter}
        onChange={(e) => setFilter(e.target.value.toUpperCase())}
      />
      <DataTable
        columns={columns}
        rows={rows}
        storageKey="scorecard"
        glossary={glossary}
        renderCell={renderScorecardCell}
        rowClassName={(row) => (row.flagged ? "flag" : undefined)}
        pinnedFirst={pins}
      />
    </>
  );
}
