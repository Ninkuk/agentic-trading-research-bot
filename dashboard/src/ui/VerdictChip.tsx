// A one-line verdict chip on the shadcn Badge component — the tone maps to
// Badge's tinted up/down/hold variants (the lab palette, defined once in
// components/ui/badge.tsx for both themes). The text is always the primary
// channel — color is never the only signal (a colorblind reader, or a
// printed/grayscale copy, still gets "Risk-on" vs "Risk-off").

import type { Tone, Verdict } from "../types";
import { Badge } from "../components/ui/badge";

const TONE_VARIANT: Record<Tone, "up" | "down" | "hold"> = {
  on: "up",
  off: "down",
  mid: "hold",
};

export interface VerdictChipProps {
  verdict: Verdict;
  /** Extra classes — the summary card's chip reads at text-sm (lab spec). */
  className?: string;
}

export function VerdictChip({ verdict, className }: VerdictChipProps) {
  return (
    <Badge
      variant={TONE_VARIANT[verdict.tone]}
      className={["verdict-chip", `verdict-chip--${verdict.tone}`, className]
        .filter(Boolean)
        .join(" ")}
    >
      {verdict.text}
    </Badge>
  );
}
