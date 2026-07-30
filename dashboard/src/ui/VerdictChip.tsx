// A one-line verdict pill. The tone drives the color, but the text is
// always the primary channel — color is never the only signal (a colorblind
// reader, or a printed/grayscale copy, still gets "Risk-on" vs "Risk-off").

import { tokens } from "../theme";
import type { Tone, Verdict } from "../types";

const TONE_COLOR: Record<Tone, string> = {
  on: tokens.up,
  off: tokens.down,
  mid: tokens.muted,
};

export interface VerdictChipProps {
  verdict: Verdict;
  /** Extra classes — the summary card's chip reads at text-sm (lab spec). */
  className?: string;
}

export function VerdictChip({ verdict, className }: VerdictChipProps) {
  return (
    <span
      className={["pill", "verdict-chip", `verdict-chip--${verdict.tone}`, className]
        .filter(Boolean)
        .join(" ")}
      style={{ color: TONE_COLOR[verdict.tone] }}
    >
      {verdict.text}
    </span>
  );
}
