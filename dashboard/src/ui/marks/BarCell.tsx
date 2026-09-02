// A magnitude as a bar scaled to the column's max, label after it. The
// fill is the primary ink at 70% so a full-width bar never reads louder
// than the digits beside it.

import { MARK_H, MARK_W, isFiniteNumber, roundedEndBar } from "./geometry";

export interface BarCellProps {
  value: unknown;
  max: number | null | undefined;
  format: (v: number) => string;
}

export function BarCell({ value, max, format }: BarCellProps) {
  if (!isFiniteNumber(value)) return <>—</>;
  const label = format(value);
  if (!isFiniteNumber(max) || max <= 0) return <>{label}</>;
  const len = (Math.min(Math.max(value, 0), max) / max) * MARK_W;
  return (
    <span className="bar-cell inline-flex items-center gap-1.5 align-middle" title={label}>
      <svg
        width={MARK_W}
        height={MARK_H}
        viewBox={`0 0 ${MARK_W} ${MARK_H}`}
        role="img"
        aria-label={label}
        className="shrink-0"
      >
        {len > 0 && (
          <path className="bar-fill" d={roundedEndBar(0, len, MARK_H)} fill="var(--primary)" fillOpacity={0.7} />
        )}
      </svg>
      <span className="font-mono tabular-nums">{label}</span>
    </span>
  );
}
