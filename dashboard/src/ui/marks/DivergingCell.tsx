// A signed fraction as a bar from a centre zero line, scaled to the column's
// max |v|. Both label slots are always laid out (one empty) so the zero
// lines align down a column; the label sits on the bar's outer side in
// text tokens — the tone lives in the fill only.

import { MARK_H, MARK_W, divergingLabel, isFiniteNumber, roundedEndBar } from "./geometry";

// Surface gap between the zero line and the bar's square end.
const GAP = 2;
const CENTER = MARK_W / 2;
const HALF = CENTER - GAP;

export interface DivergingCellProps {
  value: unknown;
  max: number | null | undefined;
}

export function DivergingCell({ value, max }: DivergingCellProps) {
  if (!isFiniteNumber(value)) return <>—</>;
  const label = divergingLabel(value);
  if (!isFiniteNumber(max) || max <= 0) return <>{label}</>;
  const len = (Math.min(Math.abs(value), max) / max) * HALF;
  const positive = value > 0;
  const x0 = value === 0 ? CENTER : positive ? CENTER + GAP : CENTER - GAP;
  const x1 = positive ? x0 + len : x0 - len;
  const fill = positive ? "var(--tone-up)" : "var(--tone-down)";
  const text = <span className="font-mono tabular-nums">{label}</span>;
  return (
    <span
      className="diverging-cell inline-grid grid-cols-[6ch_auto_6ch] items-center gap-1 align-middle"
      title={label}
    >
      <span className="text-right">{!positive && value !== 0 ? text : null}</span>
      <svg
        width={MARK_W}
        height={MARK_H}
        viewBox={`0 0 ${MARK_W} ${MARK_H}`}
        role="img"
        aria-label={label}
        className="shrink-0"
      >
        <line
          className="diverging-zero"
          x1={CENTER}
          x2={CENTER}
          y1={0}
          y2={MARK_H}
          stroke="var(--border)"
          strokeWidth="1"
        />
        {value !== 0 && (
          <path
            className={`diverging-bar diverging-bar--${positive ? "up" : "down"}`}
            d={roundedEndBar(x0, x1, MARK_H)}
            fill={fill}
          />
        )}
      </svg>
      <span className="text-left">{positive || value === 0 ? text : null}</span>
    </span>
  );
}
