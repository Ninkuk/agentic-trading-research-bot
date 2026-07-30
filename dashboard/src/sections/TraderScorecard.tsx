// Track record (id "plan-004-scorecard"): the plan-004 plain-text report
// (scorer/scorecard.py's `build_report`), reused verbatim — data.py's
// `_trader_scorecard` docstring is explicit that this is `text_lines` only,
// never columns/rows, and carries no `empty` state (the report always
// renders a full structure, even a thin one).

import type { Glossary, Section } from "../types";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function TraderScorecard({ sec }: SectionComponentProps) {
  const lines = sec.text_lines ?? [];
  return <pre className="mono">{lines.join("\n")}</pre>;
}
