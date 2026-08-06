// Signals strand flagship: every scored ticker's net vote. The "symbol"
// column is a link to the ticker drill-down; every other column renders
// through the shared lab heuristics (tinted signed score, coverage %,
// staleness "Nd", held pill — see ui/sectionCells.tsx). Flagged rows keep
// the ★ + amber-tint treatment via DataTable's `rowClassName` hook
// (tr.flag / tr.flag .sym::after in index.css). The ticker filter keeps
// the legacy `#tickfilter` id, persisted via usePrefs so a filter typed
// tonight survives a reload. `pinnedFirst` reads the same
// `usePrefs("pins", [])` list TickerDetail's pin toggle writes — a ticker
// pinned from its drill-down page groups above the rest here too, active
// sort still applying within each group.

import { type ReactNode } from "react";
import { Search } from "lucide-react";
import { usePrefs } from "../hooks/usePrefs";
import type { Column, Glossary, Row, Section } from "../types";
import { Input } from "../components/ui/input";
import { DataTable } from "../ui/DataTable";
import { sectionCell } from "../ui/sectionCells";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
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
  // Everything else — the tinted signed score (the lab design; the old
  // diverging ScoreBar and the 3-point trend sparkline are both retired),
  // coverage as a percent, staleness as "Nd", held as a pill — comes from
  // the shared lab heuristics. The full score history lives on the ticker
  // drill-down chart, one click away via the symbol link.
  return sectionCell(row, col);
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
    <div className="space-y-2.5">
      {/* Same visual language as DataTable's built-in filter (sentence-case
          placeholder, row count on the right) — two filter styles for one
          job read as two different products. Typed value still uppercases:
          tickers are uppercase. */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative w-full max-w-56">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
          <Input
            id="tickfilter"
            type="search"
            placeholder="Filter tickers…"
            aria-label="Filter tickers"
            className="h-8 pl-8 text-sm"
            value={filter}
            onChange={(e) => setFilter(e.target.value.toUpperCase())}
          />
        </div>
        <span className="text-muted-foreground text-xs whitespace-nowrap tabular-nums">
          {rows.length} of {allRows.length} rows
        </span>
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        storageKey="scorecard"
        glossary={glossary}
        renderCell={renderScorecardCell}
        rowClassName={(row) => (row.flagged ? "flag" : undefined)}
        pinnedFirst={pins}
        filterable={false}
      />
    </div>
  );
}
