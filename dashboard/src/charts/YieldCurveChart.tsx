// The Treasury curve as a line over an ordinal maturity axis (3m → 2y →
// 10y). Same ChartContainer + measured-width + responsive={false} pattern
// as RegimeTimeline: ResponsiveContainer is 0x0 in jsdom.

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";

export interface YieldCurvePoint {
  /** Short axis label, e.g. "3m", "2y". */
  label: string;
  months: number;
  yield: number;
}

const curveConfig = { yield: { label: "yield %", color: "var(--chart-2)" } } satisfies ChartConfig;

export function YieldCurveChart({ points, height = 180 }: { points: YieldCurvePoint[]; height?: number }) {
  const { ref, width } = useMeasuredWidth(480);
  const data = [...points].sort((a, b) => a.months - b.months);
  const ys = data.map((p) => p.yield);
  // Pad the auto domain so the end dots don't sit on the frame.
  const pad = Math.max(0.1, (Math.max(...ys) - Math.min(...ys)) * 0.25);
  return (
    <div ref={ref} className="yield-curve-chart w-full">
      <ChartContainer
        config={curveConfig}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <LineChart width={width} height={height} data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="label" type="category" interval={0} tickLine={false} axisLine={false} tickMargin={8} />
          <YAxis
            width={36}
            tickLine={false}
            axisLine={false}
            domain={[(min: number) => min - pad, (max: number) => max + pad]}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                valueFormatter={(v) => (typeof v === "number" ? `${v.toFixed(2)}%` : String(v))}
              />
            }
          />
          <Line
            className="yield-curve-line"
            dataKey="yield"
            type="monotone"
            stroke="var(--color-yield)"
            strokeWidth={2}
            dot={{ r: 4, fill: "var(--color-yield)", strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ChartContainer>
    </div>
  );
}
