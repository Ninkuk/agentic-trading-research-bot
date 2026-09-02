// oxlint-disable react/only-export-components -- geometry helpers are
// exported for tests; there is one component here for fast refresh to preserve.
//
// One horizontal proportion bar for the open-thesis verdict mix. Pure SVG:
// three tone segments split by 2px gaps in the card color, outer ends
// rounded via a clip on the whole bar so the interior joins stay square.
// Counts ride below as text ("SOUND 47") — the tone only echoes the word.

export interface VerdictCounts {
  SOUND: number;
  UNPROVEN: number;
  FLAWED: number;
}

export const VERDICT_MIX_WIDTH = 600;
const BAR_H = 12;
const GAP = 2;
const RADIUS = 4;

const SEGMENTS: { key: keyof VerdictCounts; color: string }[] = [
  { key: "SOUND", color: "var(--tone-up)" },
  { key: "UNPROVEN", color: "var(--tone-hold)" },
  { key: "FLAWED", color: "var(--tone-down)" },
];

export interface VerdictSegment {
  key: keyof VerdictCounts;
  count: number;
  x: number;
  width: number;
  color: string;
}

/** Segment geometry in viewBox units; zero-count verdicts take no slot. */
export function verdictSegments(counts: VerdictCounts, width = VERDICT_MIX_WIDTH): VerdictSegment[] {
  const present = SEGMENTS.filter((s) => counts[s.key] > 0);
  const total = present.reduce((sum, s) => sum + counts[s.key], 0);
  if (total === 0) return [];
  const usable = width - GAP * (present.length - 1);
  let x = 0;
  return present.map((s) => {
    const w = (counts[s.key] / total) * usable;
    const seg = { key: s.key, count: counts[s.key], x, width: w, color: s.color };
    x += w + GAP;
    return seg;
  });
}

export function VerdictMix({ counts }: { counts: VerdictCounts }) {
  const segments = verdictSegments(counts);
  if (segments.length === 0) return null;
  const total = segments.reduce((sum, s) => sum + s.count, 0);
  const title = segments.map((s) => `${s.key} ${s.count}`).join(" · ");
  return (
    <div className="verdict-mix space-y-1.5">
      <svg
        className="block w-full"
        viewBox={`0 0 ${VERDICT_MIX_WIDTH} ${BAR_H}`}
        preserveAspectRatio="none"
        height={BAR_H}
        role="img"
        aria-label={`Verdict mix of ${total} open theses: ${title}`}
      >
        <title>{title}</title>
        <defs>
          <clipPath id="verdict-mix-clip">
            <rect x={0} y={0} width={VERDICT_MIX_WIDTH} height={BAR_H} rx={RADIUS} />
          </clipPath>
        </defs>
        <g clipPath="url(#verdict-mix-clip)">
          {segments.map((s) => (
            <rect
              key={s.key}
              data-verdict={s.key}
              x={s.x}
              y={0}
              width={s.width}
              height={BAR_H}
              fill={s.color}
            />
          ))}
        </g>
      </svg>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {segments.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-sm" style={{ background: s.color }} aria-hidden="true" />
            <span className="text-muted-foreground">{s.key}</span>
            <span className="font-mono tabular-nums">{s.count}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
