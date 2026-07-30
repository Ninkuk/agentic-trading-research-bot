import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../fixtures/data.json";
import type { DashboardDoc } from "../types";
import { Main } from "./Main";

const doc = fixture as unknown as DashboardDoc;

beforeEach(() => {
  localStorage.clear();
  location.hash = "";
});

test("renders every hero bullet", () => {
  render(<Main doc={doc} />);
  for (const bullet of doc.hero.bullets) {
    expect(screen.getByText(bullet.text)).toBeInTheDocument();
  }
});

test("renders all five strand headings in order", () => {
  render(<Main doc={doc} />);
  const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  const strandOrder = ["Macro", "Signals", "Research", "Track record", "Your book"];
  const indices = strandOrder.map((label) => headings.indexOf(label));
  for (const idx of indices) expect(idx).toBeGreaterThanOrEqual(0);
  expect(indices).toEqual([...indices].sort((a, b) => a - b));
});

test("a section with an error shows the unavailable note instead of crashing", () => {
  render(<Main doc={doc} />);
  expect(screen.getByText(/unavailable \(stocks\.db/i)).toBeInTheDocument();
});

test("the masthead search box navigates to the ticker route on Enter, uppercased", async () => {
  render(<Main doc={doc} />);
  const input = screen.getByRole("textbox", { name: /search ticker/i });
  await userEvent.type(input, "deck{Enter}");
  expect(location.hash).toBe("#/ticker/DECK");
});

test("an unregistered section id falls back to the generic DataTable renderer", () => {
  render(<Main doc={doc} />);
  // "scorecard" has no dedicated component registered in Task 13 — it must
  // still render its columns and rows via GenericSection, not go blank.
  expect(screen.getByRole("columnheader", { name: /symbol/i })).toBeInTheDocument();
  expect(screen.getByText("AAPL")).toBeInTheDocument();
});

test("regime section renders its tiles and drivers table", () => {
  render(<Main doc={doc} />);
  // The regime verdict shows twice by design: once compact in the KPI row,
  // once again in the Macro strand's Regime section header.
  expect(screen.getAllByText("Risk-on, 3rd night").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("VIX level")).toBeInTheDocument();
});
