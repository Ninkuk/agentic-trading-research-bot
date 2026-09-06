import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Column, Glossary, Row } from "../types";
import { DataTable } from "./DataTable";

const COLS: Column[] = [
  { key: "score", label: "Score", numeric: true, direction: null, term: null },
  { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
];

const ROWS3: Row[] = [
  { score: 5, symbol: "AAA" },
  { score: 1, symbol: "BBB" },
  { score: 9, symbol: "CCC" },
];

const ROWS10: Row[] = Array.from({ length: 10 }, (_, i) => ({ score: i, symbol: `S${i}` }));

function cellTexts(colIndex: number): string[] {
  const rows = screen.getAllByRole("row").slice(1); // drop the header row
  return rows.map((row) => within(row).getAllByRole("cell")[colIndex]?.textContent ?? "");
}

beforeEach(() => {
  localStorage.clear();
});

test("numeric sort toggles and shows indicator", async () => {
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t1" />);
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(0)).toEqual(["9", "5", "1"]); // desc first
  expect(screen.getByRole("columnheader", { name: /score/i })).toHaveAttribute(
    "aria-sort",
    "descending",
  );
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(0)).toEqual(["1", "5", "9"]);
  expect(screen.getByRole("columnheader", { name: /score/i })).toHaveAttribute(
    "aria-sort",
    "ascending",
  );
});

test("keyboard: focusing the sort button and pressing Enter applies the sort", async () => {
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t5" />);
  const sortButton = screen.getByRole("button", { name: /sort by score/i });
  sortButton.focus();
  expect(sortButton).toHaveFocus();
  await userEvent.keyboard("{Enter}");
  expect(cellTexts(0)).toEqual(["9", "5", "1"]); // desc first, same as the click-sort test
  expect(screen.getByRole("columnheader", { name: /score/i })).toHaveAttribute(
    "aria-sort",
    "descending",
  );
});

test("rows beyond the page size sit on later pages; next/previous walk them", async () => {
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2" initialRows={3} />);
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3);
  expect(screen.getByText("1–3 of 10")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /previous page/i })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: /next page/i }));
  expect(cellTexts(1)).toEqual(["S3", "S4", "S5"]);
  expect(screen.getByText("4–6 of 10")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /previous page/i }));
  expect(cellTexts(1)).toEqual(["S0", "S1", "S2"]);
});

test("the last page is short and disables next", async () => {
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2b" initialRows={3} />);
  const next = screen.getByRole("button", { name: /next page/i });
  await userEvent.click(next);
  await userEvent.click(next);
  await userEvent.click(next);
  expect(cellTexts(1)).toEqual(["S9"]);
  expect(screen.getByText("10–10 of 10")).toBeInTheDocument();
  expect(next).toBeDisabled();
});

test("tables that fit on one page render no pager", () => {
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t2c" initialRows={3} />);
  expect(screen.queryByRole("button", { name: /next page/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/of 3/)).not.toBeInTheDocument();
});

test("typing a filter returns to the first page of the matches", async () => {
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2d" initialRows={3} />);
  await userEvent.click(screen.getByRole("button", { name: /next page/i }));
  await userEvent.click(screen.getByRole("button", { name: /next page/i }));
  expect(cellTexts(1)).toEqual(["S6", "S7", "S8"]);
  await userEvent.type(screen.getByLabelText(/filter rows/i), "S");
  expect(cellTexts(1)).toEqual(["S0", "S1", "S2"]);
  expect(screen.getByText("1–3 of 10")).toBeInTheDocument();
});

test("the page never persists across visits", async () => {
  const { unmount } = render(
    <DataTable columns={COLS} rows={ROWS10} storageKey="t2e" initialRows={3} />,
  );
  await userEvent.click(screen.getByRole("button", { name: /next page/i }));
  expect(cellTexts(1)).toEqual(["S3", "S4", "S5"]);
  unmount();
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2e" initialRows={3} />);
  expect(cellTexts(1)).toEqual(["S0", "S1", "S2"]);
});

test("a legacy persisted expanded flag is ignored", () => {
  localStorage.setItem(
    "atrb:t7",
    JSON.stringify({ sortKey: null, sortDir: null, expanded: true }),
  );
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t7" initialRows={3} />);
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3);
});

test("a column whose label matches a glossary key gets a popover without an explicit term", async () => {
  const glossary: Glossary = {
    "Confidence interval (CI)": "a range around a measured result.",
    "Book heat / Heat": "money riding on current positions.",
  };
  const cols: Column[] = [
    { key: "ci", label: "CI", numeric: true, direction: null, term: null },
    { key: "heat", label: "Heat $", numeric: true, direction: null, term: null },
  ];
  render(<DataTable columns={cols} rows={[{ ci: 1, heat: 2 }]} storageKey="t9" glossary={glossary} />);
  await userEvent.click(screen.getByRole("button", { name: "CI" }));
  expect(screen.getByRole("tooltip")).toHaveTextContent("a range around a measured result.");
  await userEvent.keyboard("{Escape}");
  await userEvent.click(screen.getByRole("button", { name: "Heat $" }));
  expect(screen.getByRole("tooltip")).toHaveTextContent("money riding on current positions.");
});

test("pinnedFirst groups pinned rows above sort", () => {
  // Row identity is the first column's value, so put "symbol" first here.
  const cols: Column[] = [
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
    { key: "score", label: "Score", numeric: true, direction: null, term: null },
  ];
  const rows: Row[] = [
    { symbol: "AAA", score: 9 },
    { symbol: "ZED", score: 1 },
    { symbol: "BBB", score: 5 },
  ];
  localStorage.setItem(
    "atrb:t4",
    JSON.stringify({ sortKey: "score", sortDir: "desc", expanded: false }),
  );
  render(<DataTable columns={cols} rows={rows} storageKey="t4" pinnedFirst={["ZED"]} />);
  expect(cellTexts(0)).toEqual(["ZED", "AAA", "BBB"]); // ZED pinned first despite lowest score
});

test("clicking a glossary term in a header opens the popover without sorting the table", async () => {
  const glossary: Glossary = { score: "The composite opinion score." };
  const cols: Column[] = [
    { key: "score", label: "Score", numeric: true, direction: null, term: "score" },
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
  ];
  render(<DataTable columns={cols} rows={ROWS3} storageKey="t6" glossary={glossary} />);
  const before = cellTexts(0);
  await userEvent.click(screen.getByRole("button", { name: "Score" }));
  expect(screen.getByRole("tooltip")).toHaveTextContent("The composite opinion score.");
  expect(cellTexts(0)).toEqual(before); // row order unchanged — the click did not sort
});

test("a column whose every value is identical is hidden (identity column exempt)", () => {
  const cols: Column[] = [
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
    { key: "held", label: "Held", numeric: false, direction: null, term: null },
    { key: "score", label: "Score", numeric: true, direction: null, term: null },
  ];
  const rows: Row[] = Array.from({ length: 5 }, (_, i) => ({
    symbol: `S${i}`,
    held: false,
    score: i,
  }));
  render(<DataTable columns={cols} rows={rows} storageKey="t10" />);
  expect(screen.queryByRole("columnheader", { name: /held/i })).not.toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: /score/i })).toBeInTheDocument();
});

test("small tables keep constant columns (a constant can still be worth reading)", () => {
  const cols: Column[] = [
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
    { key: "held", label: "Held", numeric: false, direction: null, term: null },
  ];
  const rows: Row[] = [
    { symbol: "A", held: false },
    { symbol: "B", held: false },
  ];
  render(<DataTable columns={cols} rows={rows} storageKey="t11" />);
  expect(screen.getByRole("columnheader", { name: /held/i })).toBeInTheDocument();
});

test("negative numbers render with a typographic minus in default cells", () => {
  render(
    <DataTable columns={COLS} rows={[{ score: -2, symbol: "NEG" }]} storageKey="t8" />,
  );
  expect(screen.getByText("−2")).toBeInTheDocument();
});

// Characterization tests written before the TanStack rewrite: they pin the
// behaviors the earlier suite left implicit so the rewrite cannot drop them.

test("blank cells sort last in both directions", async () => {
  const rows: Row[] = [
    { score: 5, symbol: "AAA" },
    { score: null, symbol: "NUL" },
    { score: 1, symbol: "BBB" },
  ];
  render(<DataTable columns={COLS} rows={rows} storageKey="t12" />);
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(1)).toEqual(["AAA", "BBB", "NUL"]); // desc: 5, 1, blank
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(1)).toEqual(["BBB", "AAA", "NUL"]); // asc: 1, 5, blank
});

test("the filter matches any column case-insensitively and reports the count", async () => {
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t13" initialRows={3} />);
  // Unfiltered, the pager already says how many rows there are.
  expect(screen.queryByText("10 of 10 rows")).not.toBeInTheDocument();
  await userEvent.type(screen.getByRole("textbox", { name: /filter rows/i }), "s7");
  expect(cellTexts(1)).toEqual(["S7"]);
  expect(screen.getByText("1 of 10 rows")).toBeInTheDocument();
  await userEvent.clear(screen.getByRole("textbox", { name: /filter rows/i }));
  await userEvent.type(screen.getByRole("textbox", { name: /filter rows/i }), "zzz");
  expect(screen.getByText(/no rows match "zzz"/i)).toBeInTheDocument();
});

test("filterable=false renders no filter box even on a long table", () => {
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t14" filterable={false} />);
  expect(screen.queryByRole("textbox", { name: /filter rows/i })).not.toBeInTheDocument();
});

test("sort within pinned and unpinned groups follows the active sort", async () => {
  const cols: Column[] = [
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
    { key: "score", label: "Score", numeric: true, direction: null, term: null },
  ];
  const rows: Row[] = [
    { symbol: "AAA", score: 3 },
    { symbol: "PIN1", score: 1 },
    { symbol: "BBB", score: 9 },
    { symbol: "PIN2", score: 7 },
  ];
  render(<DataTable columns={cols} rows={rows} storageKey="t15" pinnedFirst={["PIN1", "PIN2"]} />);
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(0)).toEqual(["PIN2", "PIN1", "BBB", "AAA"]); // desc inside each group
});

test("exporter-declared detail columns start hidden and a toggle reveals them", async () => {
  const cols: Column[] = [
    { key: "symbol", label: "Symbol", numeric: false, direction: null, term: null },
    { key: "net", label: "Net", numeric: true, direction: null, term: null },
    { key: "chg_long", label: "Change in longs", numeric: true, direction: null, term: null, hidden: true },
    { key: "chg_short", label: "Change in shorts", numeric: true, direction: null, term: null, hidden: true },
  ];
  const rows: Row[] = [
    { symbol: "A", net: 1, chg_long: 5, chg_short: 6 },
    { symbol: "B", net: 2, chg_long: 7, chg_short: 8 },
  ];
  render(<DataTable columns={cols} rows={rows} storageKey="t12" />);
  expect(screen.queryByRole("columnheader", { name: /change in longs/i })).not.toBeInTheDocument();
  const btn = screen.getByRole("button", { name: /2 more columns/i });
  expect(btn).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(btn);
  expect(screen.getByRole("columnheader", { name: /change in longs/i })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: /change in shorts/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /fewer columns/i })).toHaveAttribute("aria-pressed", "true");
});

test("no detail columns means no columns toggle", () => {
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t13" />);
  expect(screen.queryByRole("button", { name: /more columns/i })).not.toBeInTheDocument();
});
