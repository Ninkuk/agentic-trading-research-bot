// Pure y-domain rule for DriverChart, kept out of the component file so
// the chart module exports only components (fast refresh).

import type { Tile } from "../types";

export type DriverThreshold = NonNullable<Tile["thresholds"]>[number];

// A cutoff outside the data range is drawn only when the driver is within
// NEAR × its 90-day range of it, and only the nearest one per side: the line
// appears as the driver approaches a band, and a far cutoff (VIX 30 over a
// 14–22 summer) never flattens the series into a ribbon at the bottom of
// the plot. Cutoffs inside the range are always drawn.
const NEAR = 0.5;

/** The cutoffs close enough to draw, and the y-domain that includes them. */
export function driverDomain(
  values: number[],
  thresholds: DriverThreshold[],
): { domain: [number, number]; drawn: DriverThreshold[] } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.abs(max) || 1;
  const inside = thresholds.filter((t) => t.value >= min && t.value <= max);
  const below = thresholds.filter((t) => t.value < min).sort((a, b) => b.value - a.value)[0];
  const above = thresholds.filter((t) => t.value > max).sort((a, b) => a.value - b.value)[0];
  const near = [below, above].filter(
    (t): t is DriverThreshold => t !== undefined && Math.abs(t.value - (t.value < min ? min : max)) <= NEAR * span,
  );
  const drawn = [...inside, ...near].sort((a, b) => a.value - b.value);
  const lo = Math.min(min, ...drawn.map((t) => t.value));
  const hi = Math.max(max, ...drawn.map((t) => t.value));
  const pad = (hi - lo || span) * 0.12;
  return { domain: [lo - pad, hi + pad], drawn };
}
