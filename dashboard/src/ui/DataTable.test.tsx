import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Column, Row } from "../types";
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
  expect(screen.getByText("▼")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("columnheader", { name: /score/i }));
  expect(cellTexts(0)).toEqual(["1", "5", "9"]);
});

test("keyboard: focusing the sort button and pressing Enter applies the sort", async () => {
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t5" />);
  const sortButton = screen.getByRole("button", { name: /sort by score/i });
  sortButton.focus();
  expect(sortButton).toHaveFocus();
  await userEvent.keyboard("{Enter}");
  expect(cellTexts(0)).toEqual(["9", "5", "1"]); // desc first, same as the click-sort test
  expect(screen.getByText("▼")).toBeInTheDocument();
});

test("show-all reveals rows beyond initialRows and persists", async () => {
  const { unmount } = render(
    <DataTable columns={COLS} rows={ROWS10} storageKey="t2" initialRows={3} />,
  );
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3);
  await userEvent.click(screen.getByText(/show all 10/i));
  expect(screen.getAllByRole("row")).toHaveLength(1 + 10);
  unmount();
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2" initialRows={3} />);
  expect(screen.getAllByRole("row")).toHaveLength(1 + 10); // localStorage
});

test("column picker hides a column and persists", async () => {
  const { unmount } = render(<DataTable columns={COLS} rows={ROWS3} storageKey="t3" />);
  await userEvent.click(screen.getByRole("button", { name: /columns/i }));
  await userEvent.click(screen.getByRole("checkbox", { name: /score/i }));
  expect(screen.queryByRole("columnheader", { name: /score/i })).not.toBeInTheDocument();
  unmount();
  render(<DataTable columns={COLS} rows={ROWS3} storageKey="t3" />);
  expect(screen.queryByRole("columnheader", { name: /score/i })).not.toBeInTheDocument();
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
    JSON.stringify({ sortKey: "score", sortDir: "desc", expanded: false, hiddenCols: [] }),
  );
  render(<DataTable columns={cols} rows={rows} storageKey="t4" pinnedFirst={["ZED"]} />);
  expect(cellTexts(0)).toEqual(["ZED", "AAA", "BBB"]); // ZED pinned first despite lowest score
});
