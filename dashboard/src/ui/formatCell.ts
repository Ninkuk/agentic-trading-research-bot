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
  return String(value);
}
