// A sortable, filterable, expandable table on the shadcn table kit. Sort
// order and expanded state persist per `storageKey` via usePrefs — a reader
// who sorts scorecard by score sees the same layout on the next visit.
// Tables with ≥4 rows get a text filter (matches any visible column,
// case-insensitive). `pinnedFirst` (row identity = the first column's
// value) keeps specific rows above the rest regardless of sort; the active
// sort still applies within each group. `renderCell` lets a section inject
// a chart or custom formatting into a cell; `rowClassName` lets a section
// (Scorecard's flagged rows) apply a row-level CSS hook without owning row
// markup itself.

import { useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { usePrefs } from "../hooks/usePrefs";
import type { CellValue, Column, Glossary, Row } from "../types";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { formatCell } from "./formatCell";
import { Term } from "./Term";

export interface DataTableProps {
  columns: Column[];
  rows: Row[];
  storageKey: string;
  initialRows?: number;
  renderCell?: (row: Row, col: Column) => ReactNode;
  pinnedFirst?: string[];
  glossary?: Glossary;
  rowClassName?: (row: Row) => string | undefined;
  // Sections that ship their own filter UI (Scorecard's persisted symbol
  // filter) pass false so the table doesn't render a second box.
  filterable?: boolean;
}

type SortDir = "asc" | "desc" | null;

interface TableState {
  sortKey: string | null;
  sortDir: SortDir;
  expanded: boolean;
}

const DEFAULT_STATE: TableState = {
  sortKey: null,
  sortDir: null,
  expanded: false,
};

/** Tables shorter than this skip the filter chrome. */
const FILTER_MIN_ROWS = 4;

function SortIcon({ sorted, dir }: { sorted: boolean; dir: SortDir }) {
  if (!sorted)
    return (
      <ArrowUpDown className="sort-indicator sort-indicator--idle size-3.5 opacity-40" aria-hidden="true" />
    );
  return dir === "desc" ? (
    <ArrowDown className="sort-indicator text-foreground size-3.5" />
  ) : (
    <ArrowUp className="sort-indicator text-foreground size-3.5" />
  );
}

function rowKeyOf(row: Row, columns: Column[]): string {
  const idCol = columns[0];
  if (!idCol) return "";
  const v = row[idCol.key];
  return v === null || v === undefined ? "" : String(v);
}

function compareValues(a: CellValue, b: CellValue, numeric: boolean, dir: SortDir): number {
  const aBlank = a === null || a === undefined;
  const bBlank = b === null || b === undefined;
  if (aBlank || bBlank) {
    if (aBlank && bBlank) return 0;
    return aBlank ? 1 : -1; // blanks sort last regardless of direction
  }
  const cmp = numeric ? Number(a) - Number(b) : String(a).localeCompare(String(b));
  return dir === "desc" ? -cmp : cmp;
}

function sortRows(rows: Row[], col: Column | undefined, dir: SortDir): Row[] {
  if (!col || !dir) return rows;
  return [...rows].sort((r1, r2) => compareValues(r1[col.key], r2[col.key], col.numeric, dir));
}

function rowMatches(row: Row, columns: Column[], needle: string): boolean {
  return columns.some((col) => {
    const v = row[col.key];
    if (v === null || v === undefined) return false;
    return String(v).toLowerCase().includes(needle);
  });
}

export function DataTable({
  columns,
  rows,
  storageKey,
  initialRows = 8,
  renderCell,
  pinnedFirst,
  glossary = {},
  rowClassName,
  filterable: filterableProp = true,
}: DataTableProps) {
  const [state, setState] = usePrefs<TableState>(storageKey, DEFAULT_STATE);
  // Filter text is session-only on purpose — a persisted filter would make
  // tomorrow's edition open mysteriously truncated.
  const [filter, setFilter] = useState("");

  const sortCol = columns.find((c) => c.key === state.sortKey);

  const needle = filter.trim().toLowerCase();
  const filteredRows = needle ? rows.filter((r) => rowMatches(r, columns, needle)) : rows;

  const pinnedSet = new Set(pinnedFirst ?? []);
  const pinnedRows: Row[] = [];
  const restRows: Row[] = [];
  for (const row of filteredRows) {
    if (pinnedSet.has(rowKeyOf(row, columns))) pinnedRows.push(row);
    else restRows.push(row);
  }
  const processedRows = [
    ...sortRows(pinnedRows, sortCol, state.sortDir),
    ...sortRows(restRows, sortCol, state.sortDir),
  ];

  const displayedRows = state.expanded ? processedRows : processedRows.slice(0, initialRows);
  const hasMore = processedRows.length > initialRows;
  const filterable = filterableProp && rows.length >= FILTER_MIN_ROWS;

  function handleSort(col: Column): void {
    setState(
      state.sortKey === col.key
        ? { ...state, sortDir: state.sortDir === "desc" ? "asc" : "desc" }
        : { ...state, sortKey: col.key, sortDir: "desc" },
    );
  }

  function showAll(): void {
    setState({ ...state, expanded: true });
  }

  return (
    <div className="datatable space-y-2.5">
      {filterable && (
        <div className="flex items-center justify-between gap-3">
          <div className="relative w-full max-w-56">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter rows…"
              aria-label="Filter rows"
              className="h-8 pl-8 text-sm"
            />
          </div>
          <span className="text-muted-foreground text-xs whitespace-nowrap tabular-nums">
            {processedRows.length} of {rows.length} rows
          </span>
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((col) => {
              const sorted = state.sortKey === col.key;
              return (
                <TableHead
                  key={col.key}
                  role="columnheader"
                  scope="col"
                  className={`cursor-pointer whitespace-nowrap select-none ${col.numeric ? "num text-right" : ""}`}
                  aria-sort={sorted ? (state.sortDir === "asc" ? "ascending" : "descending") : "none"}
                  onClick={() => handleSort(col)}
                >
                  {/* The lab's header anatomy: a ghost Button holding the
                      label + sort arrow. Term already renders its own
                      <button> (see Term.tsx) — nesting it inside another
                      <button> would be invalid HTML and would double-fire
                      handleSort via bubbling, so term columns keep the
                      label as a sibling and the button carries only the
                      arrow. Either way every click funnels into th's
                      onClick above via bubbling, exactly once. */}
                  {col.term ? (
                    <>
                      <Term term={col.term} glossary={glossary}>
                        {col.label}
                      </Term>
                      {col.direction === "up-good" && (
                        <span className="dir-hint text-muted-foreground/70 text-[10px] font-normal"> ↑ better</span>
                      )}
                      {col.direction === "down-good" && (
                        <span className="dir-hint text-muted-foreground/70 text-[10px] font-normal"> ↓ better</span>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="sort-trigger ml-0.5 h-8 px-1.5"
                        aria-label={`Sort by ${col.label}`}
                      >
                        <SortIcon sorted={sorted} dir={state.sortDir} />
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`sort-trigger -ml-2 h-8 gap-1.5 px-2 text-xs font-medium ${
                        col.numeric ? "-mr-2 ml-auto flex" : ""
                      }`}
                      aria-label={`Sort by ${col.label}`}
                    >
                      <span className="col-label">{col.label}</span>
                      {col.direction === "up-good" && (
                        <span className="dir-hint text-muted-foreground/70 text-[10px] font-normal">↑ better</span>
                      )}
                      {col.direction === "down-good" && (
                        <span className="dir-hint text-muted-foreground/70 text-[10px] font-normal">↓ better</span>
                      )}
                      <SortIcon sorted={sorted} dir={state.sortDir} />
                    </Button>
                  )}
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {needle && processedRows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-muted-foreground h-14 text-center">
                No rows match "{filter}".
              </TableCell>
            </TableRow>
          ) : (
            displayedRows.map((row, i) => (
              <TableRow key={`${rowKeyOf(row, columns)}:${i}`} className={rowClassName?.(row)}>
                {columns.map((col) => (
                  <TableCell
                    key={col.key}
                    className={col.numeric ? "num text-right font-mono tabular-nums" : undefined}
                  >
                    {renderCell ? renderCell(row, col) : formatCell(row[col.key])}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {hasMore && !state.expanded && (
        <button
          type="button"
          className="show-all text-muted-foreground hover:text-foreground cursor-pointer border-0 bg-transparent p-0 pt-1 text-xs font-medium underline underline-offset-2"
          onClick={showAll}
        >
          Show all {processedRows.length}
        </button>
      )}
    </div>
  );
}
