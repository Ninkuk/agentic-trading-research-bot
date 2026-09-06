// A sortable, filterable, paged table: TanStack Table (v9 feature API)
// for row-model state, the shadcn table kit for markup — the layout the
// shadcn "Data Table" guide prescribes. Sort order persists per `storageKey`
// via usePrefs — a reader who sorts scorecard by score sees the same layout
// on the next visit. The page is session-only on purpose (like filter
// text): sort is a stable preference, "page 40 of 144" is a momentary act.
// Paging happens outside the row model, after pinned-first partitioning,
// so a pinned row leads page one instead of being pinned within whatever
// page its sort position lands on.
// Tables with ≥4 rows get a text filter (matches any column, including
// auto-hidden ones, case-insensitive). `pinnedFirst` (row identity = the
// first column's value) keeps specific rows above the rest regardless of
// sort; the active sort still applies within each group. `renderCell` lets
// a section inject a chart or custom formatting into a cell; `rowClassName`
// lets a section (Scorecard's flagged rows) apply a row-level CSS hook
// without owning row markup itself.

import { useMemo, useState, type ReactNode } from "react";
import {
  columnFilteringFeature,
  columnVisibilityFeature,
  createFilteredRowModel,
  createSortedRowModel,
  globalFilteringFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
  type ColumnDef,
  type ColumnVisibilityState,
  type Row as TableRowModel,
  type SortFn,
  type SortingState,
  type Updater,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { usePrefs } from "../hooks/usePrefs";
import type { Column, Glossary, Row } from "../types";
import { Button } from "../components/ui/button";
import { InputGroup, InputGroupAddon, InputGroupInput } from "../components/ui/input-group";
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
  /** Rows per page. */
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

// Older persisted blobs also carried an `expanded` key; it parses fine and
// is simply no longer read (see the header comment on the session-only
// page).
interface TableState {
  sortKey: string | null;
  sortDir: SortDir;
}

const DEFAULT_STATE: TableState = {
  sortKey: null,
  sortDir: null,
};

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  columnVisibilityFeature,
});

type Features = typeof features;
type ModelRow = TableRowModel<Features, Row>;

/** Lowercased, parenthetical-free, alphanumeric-only form for matching
 * column labels against glossary keys ("FCF yield %" → "fcfyield"). */
function normalizeKey(s: string): string {
  return s
    .replace(/\([^)]*\)/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

/** Index glossary keys by normalized form, including each half of
 * slash-compound keys ("Book heat / Heat" answers for "Heat $") and any
 * parenthetical alias ("Confidence interval (CI)" answers for "CI"). */
function buildGlossaryIndex(glossary: Glossary): Map<string, string> {
  const index = new Map<string, string>();
  for (const key of Object.keys(glossary)) {
    const paren = /\(([^)]+)\)/.exec(key);
    const candidates = [key, ...key.split("/")];
    if (paren?.[1]) candidates.push(paren[1]);
    for (const candidate of candidates) {
      const norm = normalizeKey(candidate);
      if (norm && !index.has(norm)) index.set(norm, key);
    }
  }
  return index;
}

/** The exporter's explicit `term` wins; otherwise fall back to a
 * normalized label match so a glossary entry that plainly names the
 * column still gets its popover without an exporter change. */
function termForColumn(
  col: Column,
  glossary: Glossary,
  index: Map<string, string>,
): string | undefined {
  if (col.term && glossary[col.term] !== undefined) return col.term;
  return index.get(normalizeKey(col.label));
}

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

// Blank-last ordering is TanStack's `sortUndefined: "last"`, which it
// applies before the direction flip — so blanks stay last in both
// directions. It only recognises undefined, hence the null→undefined
// accessor below; these comparators never see a blank.
const sortNumeric: SortFn<Features, Row> = (a, b, id) =>
  Number(a.getValue(id)) - Number(b.getValue(id));
const sortText: SortFn<Features, Row> = (a, b, id) =>
  String(a.getValue(id)).localeCompare(String(b.getValue(id)));

function rowMatches(row: Row, columns: Column[], needle: string): boolean {
  return columns.some((col) => {
    const v = row[col.key];
    if (v === null || v === undefined) return false;
    return String(v).toLowerCase().includes(needle);
  });
}

function toSorting(state: TableState): SortingState {
  return state.sortKey && state.sortDir
    ? [{ id: state.sortKey, desc: state.sortDir === "desc" }]
    : [];
}

function fromSorting(sorting: SortingState): TableState {
  const first = sorting[0];
  return first
    ? { sortKey: first.id, sortDir: first.desc ? "desc" : "asc" }
    : DEFAULT_STATE;
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
  // Filter text and page are session-only on purpose — a persisted filter
  // would make tomorrow's edition open mysteriously truncated, and a
  // persisted page would open it mid-list.
  const [filter, setFilter] = useState("");
  // The page is stored with the filter+sort it was chosen under; a change
  // to either reads as page one without an effect-driven reset.
  const [paging, setPaging] = useState<{ index: number; under: string }>({ index: 0, under: "" });
  // Detail columns (`col.hidden`) stay folded until asked for; session-only
  // like the page, so a wide table never reopens as a wall.
  const [showDetail, setShowDetail] = useState(false);
  const detailCount = columns.filter((c) => c.hidden).length;

  const glossaryIndex = useMemo(() => buildGlossaryIndex(glossary), [glossary]);
  const columnByKey = useMemo(() => new Map(columns.map((c) => [c.key, c])), [columns]);

  const columnDefs = useMemo<ColumnDef<Features, Row>[]>(
    () =>
      columns.map((col) => ({
        id: col.key,
        accessorFn: (row: Row) => row[col.key] ?? undefined,
        sortFn: col.numeric ? sortNumeric : sortText,
        sortUndefined: "last",
        sortDescFirst: true,
        cell: ({ row }) => (renderCell ? renderCell(row.original, col) : formatCell(row.original[col.key])),
      })),
    [columns, renderCell],
  );

  // A column whose every value is identical carries zero information —
  // "Held: no" × 27 rows is grid noise, not data. Hide it (identity column
  // exempt; small tables exempt, where a constant can still be worth
  // reading). Computed from the full row set, not the filtered one, so
  // filtering can't make columns pop in and out.
  const columnVisibility = useMemo<ColumnVisibilityState>(() => {
    const hidden: ColumnVisibilityState = {};
    if (!showDetail) columns.forEach((col) => col.hidden && (hidden[col.key] = false));
    if (rows.length < FILTER_MIN_ROWS) return hidden;
    columns.forEach((col, i) => {
      if (i === 0) return;
      const first = rows[0]?.[col.key] ?? null;
      if (Array.isArray(first)) return;
      if (rows.every((r) => (r[col.key] ?? null) === first)) hidden[col.key] = false;
    });
    return hidden;
  }, [columns, rows, showDetail]);

  const sorting = useMemo(() => toSorting(state), [state]);
  const needle = filter.trim().toLowerCase();

  const table = useTable({
    features,
    columns: columnDefs,
    data: rows,
    state: { sorting, columnVisibility, globalFilter: needle },
    onSortingChange: (updater: Updater<SortingState>) =>
      setState(fromSorting(typeof updater === "function" ? updater(sorting) : updater)),
    enableSortingRemoval: false,
    enableMultiSort: false,
    // The old-column check would otherwise decide filterability from the
    // first row's value type, dropping a column whose first cell is blank.
    getColumnCanGlobalFilter: () => true,
    globalFilterFn: (row: ModelRow, _id: string, value: string) =>
      rowMatches(row.original, columns, value),
  });

  const modelRows = table.getRowModel().rows;
  const pinnedSet = new Set(pinnedFirst ?? []);
  const pinnedRows: ModelRow[] = [];
  const restRows: ModelRow[] = [];
  for (const row of modelRows) {
    if (pinnedSet.has(rowKeyOf(row.original, columns))) pinnedRows.push(row);
    else restRows.push(row);
  }
  const processedRows = [...pinnedRows, ...restRows];

  const pageSize = Math.max(1, initialRows);
  const pageCount = Math.max(1, Math.ceil(processedRows.length / pageSize));
  const pagingUnder = `${needle}\u0000${state.sortKey ?? ""}\u0000${state.sortDir ?? ""}`;
  const pageIndex = Math.min(paging.under === pagingUnder ? paging.index : 0, pageCount - 1);
  const goToPage = (index: number) => setPaging({ index, under: pagingUnder });
  const pageStart = pageIndex * pageSize;
  const displayedRows = processedRows.slice(pageStart, pageStart + pageSize);
  const paged = processedRows.length > pageSize;
  const filterable = filterableProp && rows.length >= FILTER_MIN_ROWS;
  const visibleCount = table.getVisibleLeafColumns().length;

  const detailToggle = detailCount > 0 && (
    <Button
      variant="ghost"
      size="sm"
      aria-pressed={showDetail}
      onClick={() => setShowDetail((v) => !v)}
    >
      {showDetail ? "Fewer columns" : `${detailCount} more columns`}
    </Button>
  );

  return (
    <div className="datatable space-y-2.5">
      {!filterable && detailToggle && <div className="flex justify-end">{detailToggle}</div>}
      {filterable && (
        <div className="flex items-center justify-between gap-3">
          <InputGroup className="w-full max-w-56">
            <InputGroupInput
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter rows…"
              aria-label="Filter rows"
            />
            <InputGroupAddon>
              <Search />
            </InputGroupAddon>
          </InputGroup>
          {/* Match count only while filtering — unfiltered, the pager's
              "1–8 of N" already carries the total. */}
          <div className="flex items-center gap-3">
            {needle && (
              <span className="text-muted-foreground text-xs whitespace-nowrap tabular-nums">
                {processedRows.length} of {rows.length} rows
              </span>
            )}
            {detailToggle}
          </div>
        </div>
      )}
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => {
                const col = columnByKey.get(header.column.id);
                if (!col) return null;
                const sortedDir = header.column.getIsSorted();
                const sorted = sortedDir !== false;
                const term = termForColumn(col, glossary, glossaryIndex);
                return (
                  <TableHead
                    key={header.id}
                    role="columnheader"
                    scope="col"
                    className={`cursor-pointer whitespace-nowrap select-none ${col.numeric ? "num text-right" : ""}`}
                    aria-sort={sorted ? (sortedDir === "asc" ? "ascending" : "descending") : "none"}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {/* The lab's header anatomy: a ghost Button holding the
                        label + sort arrow. Term already renders its own
                        <button> (see Term.tsx) — nesting it inside another
                        <button> would be invalid HTML and would double-fire
                        the sort via bubbling, so term columns keep the
                        label as a sibling and the button carries only the
                        arrow. Either way every click funnels into th's
                        onClick above via bubbling, exactly once. */}
                    {term ? (
                      <span
                        className={`inline-flex h-8 items-center gap-1.5 text-xs font-medium ${
                          col.numeric ? "justify-end" : ""
                        }`}
                      >
                        <Term term={term} glossary={glossary}>
                          {col.label}
                        </Term>
                        {col.direction === "up-good" && (
                          <span className="dir-hint text-muted-foreground text-xs font-normal">↑ better</span>
                        )}
                        {col.direction === "down-good" && (
                          <span className="dir-hint text-muted-foreground text-xs font-normal">↓ better</span>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="sort-trigger size-6"
                          aria-label={`Sort by ${col.label}`}
                        >
                          <SortIcon sorted={sorted} dir={sortedDir || null} />
                        </Button>
                      </span>
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
                          <span className="dir-hint text-muted-foreground text-xs font-normal">↑ better</span>
                        )}
                        {col.direction === "down-good" && (
                          <span className="dir-hint text-muted-foreground text-xs font-normal">↓ better</span>
                        )}
                        <SortIcon sorted={sorted} dir={sortedDir || null} />
                      </Button>
                    )}
                  </TableHead>
                );
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {needle && processedRows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={visibleCount} className="text-muted-foreground h-14 text-center">
                No rows match "{filter}".
              </TableCell>
            </TableRow>
          ) : (
            displayedRows.map((row) => (
              <TableRow key={row.id} className={rowClassName?.(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    className={
                      columnByKey.get(cell.column.id)?.numeric
                        ? "num text-right font-mono tabular-nums"
                        : undefined
                    }
                  >
                    <table.FlexRender cell={cell} />
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {paged && (
        <div className="pager flex items-center justify-between gap-3">
          <span className="text-muted-foreground text-xs tabular-nums">
            {`${pageStart + 1}–${pageStart + displayedRows.length} of ${processedRows.length}`}
          </span>
          <span className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="size-7"
              aria-label="Previous page"
              disabled={pageIndex === 0}
              onClick={() => goToPage(pageIndex - 1)}
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="size-7"
              aria-label="Next page"
              disabled={pageIndex >= pageCount - 1}
              onClick={() => goToPage(pageIndex + 1)}
            >
              <ChevronRight />
            </Button>
          </span>
        </div>
      )}
    </div>
  );
}
