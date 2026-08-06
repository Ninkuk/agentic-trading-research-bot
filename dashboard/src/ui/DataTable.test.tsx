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

test("show-all is a two-way toggle and never persists", async () => {
  const { unmount } = render(
    <DataTable columns={COLS} rows={ROWS10} storageKey="t2" initialRows={3} />,
  );
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3);
  await userEvent.click(screen.getByText(/show all 10/i));
  expect(screen.getAllByRole("row")).toHaveLength(1 + 10);
  await userEvent.click(screen.getByText(/show fewer/i));
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3); // collapsible again
  await userEvent.click(screen.getByText(/show all 10/i));
  unmount();
  render(<DataTable columns={COLS} rows={ROWS10} storageKey="t2" initialRows={3} />);
  expect(screen.getAllByRole("row")).toHaveLength(1 + 3); // expansion is session-only
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
