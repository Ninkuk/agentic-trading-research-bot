// Shared geometry for the inline-SVG table marks. Every mark is a fixed
// 0..W axis with the number kept as text beside it (text tokens, never the
// series color) — the mark shows shape, the digits stay the record.

import { signed } from "../../format";

export const MARK_W = 88;
export const MARK_H = 14;
export const END_RADIUS = 4;
// Range axis inset: the dot ring's radius, so an endpoint never clips.
export const RANGE_PAD = 5;

/** x for a 0..1 fraction on the range axis, clamped to the axis. */
export function rangeX(fraction: number): number {
  return RANGE_PAD + Math.min(1, Math.max(0, fraction)) * (MARK_W - RANGE_PAD * 2);
}

/** Signed fraction → "+1.2%" (the diverging mark's label and title). */
export function divergingLabel(value: number): string {
  return `${signed(value * 100, 1)}%`;
}

/** Column scale: max |v| over the finite values, or null under three of
 * them or when every value is zero — the caller then renders plain text. */
export function maxAbs(values: unknown[]): number | null {
  const finite = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (finite.length < 3) return null;
  const max = Math.max(...finite.map((v) => Math.abs(v)));
  return max > 0 ? max : null;
}

export function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** A horizontal bar from `x0` (square, at the baseline) to `x1`, the far
 * end rounded by `r`. Direction follows the sign of x1 − x0; a bar shorter
 * than `r` degrades to a square-ended sliver so it stays visible. */
export function roundedEndBar(x0: number, x1: number, h: number, r = END_RADIUS): string {
  const len = Math.abs(x1 - x0);
  const dir = x1 >= x0 ? 1 : -1;
  const f = (n: number) => n.toFixed(1);
  if (len < r) return `M${f(x0)},0 H${f(x1)} V${f(h)} H${f(x0)} Z`;
  const rr = Math.min(r, h / 2);
  const shoulder = x1 - dir * rr;
  const sweep = dir === 1 ? 1 : 0;
  return [
    `M${f(x0)},0`,
    `H${f(shoulder)}`,
    `A${rr},${rr} 0 0 ${sweep} ${f(x1)},${f(rr)}`,
    `V${f(h - rr)}`,
    `A${rr},${rr} 0 0 ${sweep} ${f(shoulder)},${f(h)}`,
    `H${f(x0)}`,
    "Z",
  ].join(" ");
}
