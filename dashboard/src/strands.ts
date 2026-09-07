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

export function strandLabels(
  sections: Record<SectionId, Section>,
): StrandLabel[] {
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

/** A section belongs in the strand's "Quiet tonight" list when it has no
 * rows, no tiles, no text, no chart data, and no error — just its empty
 * sentence. Quiet sections stay out of the navigation. */
export function isQuiet(sec: Section): boolean {
  if (sec.error || sec.empty === undefined) return false;
  const hasRows = Array.isArray(sec.rows) && sec.rows.length > 0;
  const hasTiles = Array.isArray(sec.tiles) && sec.tiles.length > 0;
  const hasText = Array.isArray(sec.text_lines) && sec.text_lines.length > 0;
  const hasCurve = Array.isArray(sec.curve) && sec.curve.length > 0;
  return !hasRows && !hasTiles && !hasText && !hasCurve;
}

// A long strand (Sources: ~30 cards) shows a sticky chip row and groups
// its cards under publisher headings; shorter strands read fine as-is.
export const NAV_MIN_CARDS = 8;

export interface SectionGroup {
  label: string;
  /** The publisher, when the group is one; a section with no `source`
   * is its own group, drawn without a heading. */
  source?: string;
  /** Chip target: the heading id `<strand>-<publisher>`, or the lone
   * section's own id. */
  anchor: string;
  entries: [SectionId, Section][];
}

/** Partition a strand's entries by `source`, in first-appearance order.
 * Exporter order interleaves publishers (Treasury cards sit either side
 * of CFTC's), so grouping also moves each card beside its siblings. */
export function groupBySource(
  strandSlug: string,
  entries: [SectionId, Section][],
): SectionGroup[] {
  const groups: SectionGroup[] = [];
  const bySource = new Map<string, SectionGroup>();
  for (const entry of entries) {
    const [id, sec] = entry;
    if (!sec.source) {
      groups.push({ label: sec.title ?? id, anchor: id, entries: [entry] });
      continue;
    }
    let g = bySource.get(sec.source);
    if (!g) {
      g = {
        label: sec.source,
        source: sec.source,
        anchor: `${strandSlug}-${strandId(sec.source)}`,
        entries: [],
      };
      bySource.set(sec.source, g);
      groups.push(g);
    }
    g.entries.push(entry);
  }
  return groups;
}

/** Whether a strand of these live entries gets the chip row and headings:
 * long, and spread over at least two publishers (source-less singletons
 * don't count, or every long strand would group). */
export function showsGroups(
  entries: [SectionId, Section][],
  groups: SectionGroup[],
): boolean {
  return (
    entries.length >= NAV_MIN_CARDS &&
    groups.filter((g) => g.source).length >= 2
  );
}

/** One sidebar sub-item: what the rail lists under an expanded strand.
 * `ids` are the sections it stands for, so scroll-spy on a section can
 * light the item (a publisher group spans several). */
export interface SubItem {
  label: string;
  anchor: string;
  ids: SectionId[];
}

/** The rail's sub-items for a strand: its publisher groups when it
 * groups (Sources: 11 publishers, not 30 cards), else its live sections. */
export function strandItems(
  strandSlug: string,
  entries: [SectionId, Section][],
): SubItem[] {
  const live = entries.filter(([, sec]) => !isQuiet(sec));
  const groups = groupBySource(strandSlug, live);
  if (showsGroups(live, groups)) {
    return groups.map((g) => ({
      label: g.label,
      anchor: g.anchor,
      ids: g.entries.map(([id]) => id),
    }));
  }
  return live.map(([id, sec]) => ({
    label: sec.title ?? id,
    anchor: id,
    ids: [id],
  }));
}

/** Strand slug a group anchor (`<strand>-<publisher>`) belongs to, or
 * null. Checked after strandOfSection, so a section id never shadows. */
export function strandOfAnchor(
  labels: StrandLabel[],
  anchor: string,
): string | null {
  for (const label of labels) {
    const slug = strandId(label);
    if (anchor.startsWith(`${slug}-`)) return slug;
  }
  return null;
}

/** Strand slug holding `id`, or null when no section carries that id. */
export function strandOfSection(
  sections: Record<SectionId, Section>,
  id: SectionId,
): string | null {
  const sec = sections[id];
  if (!sec) return null;
  return strandId(isStray(sec) ? "Other" : (sec.kicker as string));
}

// One sentence per strand for the Summary page's index: what lives there.
export const STRAND_BLURBS: Record<StrandLabel, string> = {
  Macro: "Tonight's regime call, the week's calendar, and the yield curve.",
  Signals: "Composite's per-ticker opinions, with how well they have graded.",
  Sources:
    "The raw feeds behind the opinions: dark pools, COT, fails, filings.",
  Research:
    "Theses on candidate names, and how research calls have panned out.",
  "Track record": "Your own fills and passes against paper outcomes and SPY.",
  "Your book":
    "Book heat, disagreements, and vol-scaled size caps on what you hold.",
  Ops: "Pipeline health, order queue, and the research worklist.",
  Other: "Sections whose strand the dashboard doesn't recognize yet.",
};
