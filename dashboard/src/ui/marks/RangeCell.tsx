// Hit rate as a dot on a 0..1 axis with its CI as a whisker and an optional
// dashed tick for the rate it must beat (null rate / drift baseline). The
// rate stays as text; the CI digits live only in the title.

import { pct } from "../../format";
import { MARK_H, MARK_W, isFiniteNumber, rangeX } from "./geometry";

export interface RangeCellProps {
  rate: unknown;
  lo: unknown;
  hi: unknown;
  tick?: unknown;
}

export function RangeCell({ rate, lo, hi, tick }: RangeCellProps) {
  if (!isFiniteNumber(rate)) return <>—</>;
  const label = pct(rate * 100, 0);
  if (!isFiniteNumber(lo) || !isFiniteNumber(hi)) return <>{label}</>;
  const tickX = isFiniteNumber(tick) ? rangeX(tick) : null;
  const ci = `CI ${Math.round(lo * 100)}–${Math.round(hi * 100)}%`;
  const title = tickX === null ? `${label}, ${ci}` : `${label}, ${ci}, beats ${pct((tick as number) * 100, 0)}`;
  const cy = MARK_H / 2;
  return (
    <span className="range-cell inline-flex items-center gap-1.5 align-middle" title={title}>
      <svg
        width={MARK_W}
        height={MARK_H}
        viewBox={`0 0 ${MARK_W} ${MARK_H}`}
        role="img"
        aria-label={title}
        className="shrink-0"
      >
        {tickX !== null && (
          <line
            className="range-tick"
            x1={tickX}
            x2={tickX}
            y1={0}
            y2={MARK_H}
            stroke="var(--muted-foreground)"
            strokeWidth="1"
            strokeDasharray="2 2"
          />
        )}
        <line
          className="range-whisker"
          x1={rangeX(lo)}
          x2={rangeX(hi)}
          y1={cy}
          y2={cy}
          stroke="var(--muted-foreground)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle className="range-ring" cx={rangeX(rate)} cy={cy} r={4.5} fill="var(--card)" />
        <circle className="range-dot" cx={rangeX(rate)} cy={cy} r={2.5} fill="var(--primary)" />
      </svg>
      <span className="font-mono tabular-nums">{label}</span>
    </span>
  );
}
