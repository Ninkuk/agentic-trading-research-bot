// A sortable, column-pickable, expandable table. Sort order, expanded
// state, and hidden columns persist per `storageKey` via usePrefs — a
// reader who hides "coverage" or sorts scorecard by score sees the same
// layout on the next visit. `pinnedFirst` (row identity = the first
// column's value) keeps specific rows above the rest regardless of sort;
// the active sort still applies within each group. `renderCell` lets a
// section inject a chart or custom formatting into a cell instead of the
// plain-text default. `rowClassName` lets a section (Scorecard's flagged
// rows) apply a row-level CSS hook without owning row markup itself.

import { useState, type ReactNode } from "react";
import { usePrefs } from "../hooks/usePrefs";
import type { CellValue, Column, Glossary, Row } from "../types";
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
  // Extra class(es) for a row's <tr> — e.g. Scorecard's "flag" class, which
  // triggers the ★ + brass left-edge treatment purely through CSS
  // (tr.flag / tr.flag .sym::after in index.css). Returning undefined
  // leaves the row unclassed.
  rowClassName?: (row: Row) => string | undefined;
}

type SortDir = "asc" | "desc" | null;

interface TableState {
  sortKey: string | null;
  sortDir: SortDir;
  expanded: boolean;
  hiddenCols: string[];
}

const DEFAULT_STATE: TableState = {
  sortKey: null,
  sortDir: null,
  expanded: false,
  hiddenCols: [],
};

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

export function DataTable({
  columns,
  rows,
  storageKey,
  initialRows = 8,
  renderCell,
  pinnedFirst,
  glossary = {},
  rowClassName,
}: DataTableProps) {
  const [state, setState] = usePrefs<TableState>(storageKey, DEFAULT_STATE);
  const [pickerOpen, setPickerOpen] = useState(false);

  const sortCol = columns.find((c) => c.key === state.sortKey);

  const pinnedSet = new Set(pinnedFirst ?? []);
  const pinnedRows: Row[] = [];
  const restRows: Row[] = [];
  for (const row of rows) {
    if (pinnedSet.has(rowKeyOf(row, columns))) pinnedRows.push(row);
    else restRows.push(row);
  }
  const processedRows = [
    ...sortRows(pinnedRows, sortCol, state.sortDir),
    ...sortRows(restRows, sortCol, state.sortDir),
  ];

  const visibleColumns = columns.filter((c) => !state.hiddenCols.includes(c.key));
  const displayedRows = state.expanded ? processedRows : processedRows.slice(0, initialRows);
  const hasMore = processedRows.length > initialRows;

  function handleSort(col: Column): void {
    setState(
      state.sortKey === col.key
        ? { ...state, sortDir: state.sortDir === "desc" ? "asc" : "desc" }
        : { ...state, sortKey: col.key, sortDir: "desc" },
    );
  }

  function toggleColumn(key: string): void {
    const hidden = new Set(state.hiddenCols);
    if (hidden.has(key)) hidden.delete(key);
    else hidden.add(key);
    setState({ ...state, hiddenCols: Array.from(hidden) });
  }

  function showAll(): void {
    setState({ ...state, expanded: true });
  }

  return (
    <div className="datatable">
      <div className="table-toolbar">
        <div className="col-picker">
          <button
            type="button"
            className="col-picker-toggle"
            aria-expanded={pickerOpen}
            onClick={() => setPickerOpen((v) => !v)}
          >
            Columns
          </button>
          {pickerOpen && (
            <div className="col-picker-menu">
              {columns.map((col) => (
                <label key={col.key} className="col-picker-item">
                  <input
                    type="checkbox"
                    checked={!state.hiddenCols.includes(col.key)}
                    onChange={() => toggleColumn(col.key)}
                  />
                  {col.label}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="twrap">
        <table>
          <thead>
            <tr>
              {visibleColumns.map((col) => {
                const sorted = state.sortKey === col.key;
                return (
                  <th
                    key={col.key}
                    role="columnheader"
                    scope="col"
                    className={col.numeric ? "num" : undefined}
                    aria-sort={sorted ? (state.sortDir === "asc" ? "ascending" : "descending") : "none"}
                    onClick={() => handleSort(col)}
                  >
                    {/* Term already renders its own <button> (see Term.tsx) — nesting
                        it inside another <button> would be invalid HTML and would
                        double-fire handleSort via bubbling, so the sort trigger
                        below is a sibling, not a wrapper, of the term label. Both
                        funnel into th's onClick above via bubbling: a click or an
                        Enter/Space-synthesized click on either fires it exactly once. */}
                    {col.term ? (
                      <Term term={col.term} glossary={glossary}>
                        {col.label}
                      </Term>
                    ) : (
                      <span className="col-label">{col.label}</span>
                    )}
                    {col.direction === "up-good" && <span className="dir-hint"> ↑ better</span>}
                    {col.direction === "down-good" && <span className="dir-hint"> ↓ better</span>}
                    <button type="button" className="sort-trigger" aria-label={`Sort by ${col.label}`}>
                      {sorted ? (
                        <span className="sort-indicator">{state.sortDir === "desc" ? "▼" : "▲"}</span>
                      ) : (
                        <span className="sort-indicator sort-indicator--idle" aria-hidden="true">
                          ⇅
                        </span>
                      )}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((row, i) => (
              <tr key={`${rowKeyOf(row, columns)}:${i}`} className={rowClassName?.(row)}>
                {visibleColumns.map((col) => (
                  <td key={col.key} className={col.numeric ? "num" : undefined}>
                    {renderCell ? renderCell(row, col) : formatCell(row[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hasMore && !state.expanded && (
        <button type="button" className="show-all" onClick={showAll}>
          Show all {processedRows.length}
        </button>
      )}
    </div>
  );
}
