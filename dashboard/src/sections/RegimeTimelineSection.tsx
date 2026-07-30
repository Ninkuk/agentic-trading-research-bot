// Wraps <RegimeTimeline> for the `regime-timeline` section. `sec.rows` is
// the generic `Row[]` bag (see types.ts); narrowed here to the chart's
// {date, regime, vix} shape since this is the one call site that knows
// what this section's rows actually contain.

import { RegimeTimeline, type RegimeTimelineRow } from "../charts/RegimeTimeline";
import type { Glossary, Row, Section } from "../types";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
}

function toTimelineRow(row: Row): RegimeTimelineRow {
  return {
    date: typeof row.date === "string" ? row.date : "",
    regime: typeof row.regime === "string" ? row.regime : null,
    vix: typeof row.vix === "number" ? row.vix : null,
  };
}

export function RegimeTimelineSection({ sec }: SectionComponentProps) {
  const rows = (sec.rows ?? []).map(toTimelineRow);
  return <RegimeTimeline rows={rows} />;
}
