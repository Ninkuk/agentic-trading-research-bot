// The summary-card KPI sparkline, verbatim from the design lab's VariantC
// KpiSpark: a bare Area in a 96x36 ChartContainer (which injects the
// per-chart --color-value variable and owns the cursor styling), hidden
// axes (X feeds the tooltip its date label; without Y the area baselines
// at 0 and a series hovering around 14 renders as a solid filled box),
// and the shadcn ChartTooltipContent floated ABOVE the chart — the
// tooltip is larger than the sparkline, so inside the viewbox it would
// cover the mark it describes. Degrades to nothing under 2 usable points.

import { Area, AreaChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";

export interface KpiSparkPoint {
  date: string;
  value: number | null;
}

export interface KpiSparkProps {
  label: string;
  points: KpiSparkPoint[];
}

export function KpiSpark({ label, points }: KpiSparkProps) {
  const usable = points.filter((p) => p.value !== null);
  if (usable.length < 2) return null;
  const config = { value: { label, color: "var(--chart-2)" } } satisfies ChartConfig;
  return (
    <ChartContainer config={config} className="aspect-auto h-9 w-24">
      <AreaChart data={usable} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <XAxis dataKey="date" hide />
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <ChartTooltip
          allowEscapeViewBox={{ x: true, y: true }}
          position={{ y: -46 }}
          wrapperStyle={{ zIndex: 20 }}
          content={
            <ChartTooltipContent
              labelFormatter={(l) => String(l)}
              valueFormatter={(v) =>
                typeof v === "number"
                  ? v.toLocaleString("en-US", { maximumFractionDigits: 2 })
                  : String(v)
              }
            />
          }
        />
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
  );
}
