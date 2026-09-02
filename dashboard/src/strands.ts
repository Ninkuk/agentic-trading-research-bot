// Strand bookkeeping shared by the sidebar (AppShell) and the page (Main):
// which strands exist tonight, which sections each holds, and which strand
// a bare section anchor belongs to. Grouping reads each section's own
// `kicker`; a kicker the frontend doesn't know lands in a trailing "Other"
// strand rather than vanishing.

import { KICKERS, type Kicker, type Section, type SectionId } from "./types";

export type StrandLabel = Kicker | "Other";

const STRAND_SET = new Set<string>(KICKERS);

export function strandId(label: string): string {
  return label.toLowerCase().replace(/\s+/g, "-");
}

function isStray(sec: Section): boolean {
  return !sec.kicker || !STRAND_SET.has(sec.kicker);
}

export function strandLabels(sections: Record<SectionId, Section>): StrandLabel[] {
  const stray = Object.values(sections).some(isStray);
  return [...KICKERS, ...(stray ? (["Other"] as const) : [])];
}

export function strandSections(
  sections: Record<SectionId, Section>,
  label: StrandLabel,
): [SectionId, Section][] {
  const entries = Object.entries(sections);
  if (label === "Other") return entries.filter(([, sec]) => isStray(sec));
  return entries.filter(([, sec]) => sec.kicker === label);
}

/** Strand slug holding `id`, or null when no section carries that id. */
export function strandOfSection(sections: Record<SectionId, Section>, id: SectionId): string | null {
  const sec = sections[id];
  if (!sec) return null;
  return strandId(isStray(sec) ? "Other" : (sec.kicker as string));
}

// One sentence per strand for the Summary page's index: what lives there.
export const STRAND_BLURBS: Record<StrandLabel, string> = {
  Macro: "Tonight's regime call, the week's calendar, and the yield curve.",
  Signals: "Composite's per-ticker opinions, with how well they have graded.",
  Sources: "The raw feeds behind the opinions: dark pools, COT, fails, filings.",
  Research: "Theses on candidate names, and how research calls have panned out.",
  "Track record": "Your own fills and passes against paper outcomes and SPY.",
  "Your book": "Book heat, disagreements, and vol-scaled size caps on what you hold.",
  Ops: "Pipeline health, order queue, and the research worklist.",
  Other: "Sections whose strand the dashboard doesn't recognize yet.",
};
