// Track record (id "trader-scorecard"): the scorecard plain-text report
// (scorer/scorecard.py's `build_report`), parsed into titled subsections +
// tables by TextReport — data.py's `_trader_scorecard` docstring is
// explicit that this is `text_lines` only, never columns/rows, and carries
// no `empty` state (the report always renders a full structure, even a
// thin one). TextReport falls back to the raw <pre> if the report format
// ever drifts past its parser.

import type { Glossary, Section } from "../types";
import { TextReport } from "../ui/TextReport";

export interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

export function TraderScorecard({ sec }: SectionComponentProps) {
  return <TextReport lines={sec.text_lines ?? []} />;
}
