// Track record: every signal's raw report card — how often it has been
// right, against the base rate it would need to beat to be worth anything.
// `renderCell` injects the EfficacyDotPlot (point estimate + 95% CI whisker
// against the null-rate band) into the "hit_rate" column, and a
// keep/watch/anti-signal/insufficient-evidence pill into "recommendation"
// (`.pill.{cls}` — mirrors sections.py's `_rec_badge`; text is always the
// primary channel, color never carries meaning alone).

import { type ReactNode } from "react";
import { EfficacyDotPlot } from "../charts/EfficacyDotPlot";
import type { CellValue, Column, Glossary, Row, Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { formatCell } from "../ui/formatCell";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

const REC_CLASS: Record<string, string> = {
  keep: "keep",
  watch: "watch",
  "anti-signal": "anti",
};

function asNumberOrNull(v: CellValue | undefined): number | null {
  return typeof v === "number" ? v : null;
}

function RecommendationPill({ value }: { value: CellValue | undefined }) {
  const text = typeof value === "string" && value ? value : "insufficient evidence";
  const cls = REC_CLASS[text] ?? "ins";
  return <span className={`pill ${cls}`}>{text}</span>;
}

function renderEfficacyCell(row: Row, col: Column): ReactNode {
  if (col.key === "hit_rate") {
    return (
      <EfficacyDotPlot
        row={{
          hit_rate: asNumberOrNull(row.hit_rate),
          hit_ci_lo: asNumberOrNull(row.hit_ci_lo),
          hit_ci_hi: asNumberOrNull(row.hit_ci_hi),
          null_rate: asNumberOrNull(row.null_rate),
        }}
      />
    );
  }
  if (col.key === "recommendation") {
    return <RecommendationPill value={row.recommendation} />;
  }
  return formatCell(row[col.key]);
}

export function SignalEfficacy({ sec, glossary }: SectionComponentProps) {
  return (
    <DataTable
      columns={sec.columns ?? []}
      rows={sec.rows ?? []}
      storageKey="signal-efficacy"
      glossary={glossary}
      renderCell={renderEfficacyCell}
    />
  );
}
