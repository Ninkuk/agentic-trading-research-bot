// A tile's history as a small multiple that owns its column (TileCharts):
// measured width, a date axis with a first/middle/last tick, the tooltip
// inside the plot, and any band cutoffs (`thresholds`, macro drivers only)
// as dashed reference lines labelled with the band above — the chart's
// job is the distance to the next band, which a sparkline cannot show.
// driverDomain decides which cutoffs are close enough to draw. Same
// ChartContainer + responsive={false} pattern as YieldCurveChart
// (ResponsiveContainer is 0x0 in jsdom). Drops below 3 usable points
// (DESIGN_MEMORY: no tiny 2-point sparklines).

import { Area, AreaChart, ReferenceLine, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import { tokens } from "../theme";
import type { Tile } from "../types";

import { axisLabel } from "./axisLabel";
import { driverDomain, type DriverThreshold } from "./driverDomain";

export type DriverPoint = NonNullable<Tile["history"]>[number];

export interface DriverChartProps {
  label: string;
  points: DriverPoint[];
  thresholds?: DriverThreshold[];
  height?: number;
}

// The first and last date labels anchor to their own edge so neither is
// clipped by the plot frame (a centred "Jul 1" at x=8 loses half itself).
function EdgeTick({
  x,
  y,
  index,
  visibleTicksCount,
  payload,
}: {
  x?: number;
  y?: number;
  index?: number;
  visibleTicksCount?: number;
  payload?: { value: string };
}) {
  const anchor = index === 0 ? "start" : index === (visibleTicksCount ?? 0) - 1 ? "end" : "middle";
  return (
    <text
      x={x}
      y={y}
      dy="0.71em"
      textAnchor={anchor}
      fontSize={11}
      fill="var(--muted-foreground)"
      className="recharts-cartesian-axis-tick-value"
    >
      {axisLabel(payload?.value)}
    </text>
  );
}

export function DriverChart({ label, points, thresholds = [], height = 112 }: DriverChartProps) {
  const { ref, width } = useMeasuredWidth(320);
  const usable = points.filter((p): p is { date: string; value: number } => p.value !== null);
  if (usable.length < 3) return null;
  const config = { value: { label, color: "var(--chart-2)" } } satisfies ChartConfig;
  const { domain, drawn } = driverDomain(
    usable.map((p) => p.value),
    thresholds,
  );
  const mid = usable[Math.floor((usable.length - 1) / 2)].date;
  const ticks = [usable[0].date, mid, usable[usable.length - 1].date];
  return (
    <div ref={ref} className="driver-chart mt-2 w-full">
      <ChartContainer
        config={config}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <AreaChart width={width} height={height} data={usable} margin={{ top: 12, right: 8, bottom: 0, left: 8 }}>
          <XAxis
            dataKey="date"
            ticks={ticks}
            interval={0}
            tick={<EdgeTick />}
            tickLine={false}
            axisLine={false}
            tickMargin={6}
          />
          <YAxis hide domain={domain} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(l) => axisLabel(String(l))}
                valueFormatter={(v) =>
                  typeof v === "number"
                    ? v.toLocaleString("en-US", { maximumFractionDigits: 2 })
                    : String(v)
                }
              />
            }
          />
          {drawn.map((t) => (
            <ReferenceLine
              key={t.value}
              y={t.value}
              stroke={tokens.edge}
              strokeDasharray="3 3"
              className="driver-threshold"
              label={{
                value: t.above,
                position: "insideTopLeft",
                fontSize: 11,
                fill: "var(--muted-foreground)",
              }}
            />
          ))}
          <Area
            dataKey="value"
            type="monotone"
            stroke="var(--color-value)"
            strokeWidth={1.5}
            fill="var(--color-value)"
            fillOpacity={0.15}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartContainer>
    </div>
  );
}
