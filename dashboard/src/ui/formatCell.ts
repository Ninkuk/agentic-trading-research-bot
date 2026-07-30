// DataTable's default per-cell text formatting, split out of DataTable.tsx
// so that file stays component-only (oxlint's react-refresh rule flags a
// plain function export alongside a component). Sections whose `renderCell`
// only special-cases a couple of columns (Scorecard, SignalEfficacy,
// ResearchReopens) fall back to this for every other column, so their
// formatting still matches DataTable's own default.

import type { ReactNode } from "react";
import type { CellValue } from "../types";

export function formatCell(value: CellValue | undefined): ReactNode {
  if (value === undefined || value === null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return "—";
  if (typeof value === "number") {
    // Cap at 2 decimal places — SQL view outputs (avg returns, z-scores)
    // carry full float precision the table shouldn't display. Integers stay
    // integers (no trailing ".00"), and the sign comes from the ROUNDED
    // value so -0.004 renders "0", not "−0". Typographic minus for
    // negatives — signed()/usd() already use it, so the default cell path
    // must agree or the same table mixes "-2" and "−2".
    const abs = Math.abs(value);
    // Abbreviate at millions/billions: dollar-volume cells arrive as raw
    // floats like 14967000806.137735 and are unreadable at full width.
    if (abs >= 1e6) {
      const [div, suffix] = abs >= 1e9 ? [1e9, "B"] : [1e6, "M"];
      const body = `${Math.round((abs / div) * 100) / 100}${suffix}`;
      return value < 0 ? `−${body}` : body;
    }
    const rounded = Math.round(value * 100) / 100;
    return rounded < 0 ? `−${String(Math.abs(rounded))}` : String(rounded);
  }
  return String(value);
}

// The advisor tables' dollar/percent formatting moved into
// ui/sectionCells.tsx (the shared lab heuristics) — one dispatcher for
// every table, so the identical market value can't read "$1,980.50" on the
// ticker page and "1980.5" on the main page.
