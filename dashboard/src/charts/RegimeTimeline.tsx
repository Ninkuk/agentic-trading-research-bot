// Regime timeline: a full-width VIX AreaChart inside ChartContainer (which
// owns grid/axis/cursor styling and injects --color-vix), per-night dots
// colored by that night's regime verdict via the --tone-* tokens (so they
// re-step with the theme), the shadcn ChartTooltipContent, and a caption.
//
// Width is measured from the container (ResizeObserver, explicit fallback)
// and passed with responsive={false}: jsdom measures ResponsiveContainer
// 0x0 and every geometry assertion in tests silently blanks.

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";

export interface RegimeTimelineRow {
  date: string;
  regime: string | null;
  vix: number | null;
}

export interface RegimeTimelineProps {
  rows: RegimeTimelineRow[];
  height?: number;
}

const REGIME_DOT: Record<string, string> = {
  risk_on: "var(--tone-up)",
  risk_off: "var(--tone-down)",
  mixed: "var(--tone-hold)",
};

const vixConfig = { vix: { label: "VIX", color: "var(--chart-2)" } } satisfies ChartConfig;

export function RegimeTimeline({ rows, height = 208 }: RegimeTimelineProps) {
  const { ref, width } = useMeasuredWidth(640);

  if (rows.length === 0) {
    return <p className="empty">no data</p>;
  }

  return (
    <div ref={ref} className="regime-timeline w-full">
      <ChartContainer
        config={vixConfig}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <AreaChart
          width={width}
          height={height}
          data={rows}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tickFormatter={(d: string) => d.slice(5)}
          />
          <YAxis width={32} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                valueFormatter={(v) => (typeof v === "number" ? v.toFixed(1) : String(v))}
              />
            }
          />
          <Area
            className="regime-vix-line"
            dataKey="vix"
            type="monotone"
            stroke="var(--color-vix)"
            strokeWidth={2}
            fill="var(--color-vix)"
            fillOpacity={0.12}
            isAnimationActive={false}
            connectNulls
            dot={({ cx, cy, payload, index }) =>
              cx === undefined || cy === undefined || payload.vix === null ? (
                // null-VIX nights draw no dot (the lab fixture had none;
                // live exports can) — recharts requires an element back
                <g key={index} />
              ) : (
                <circle
                  key={index}
                  className="regime-dot"
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={REGIME_DOT[String(payload.regime)] ?? "var(--color-vix)"}
                  stroke="var(--background)"
                  strokeWidth={1.5}
                />
              )
            }
          />
        </AreaChart>
      </ChartContainer>
      <p className="text-muted-foreground mt-2 text-xs">
        Dot color = that night's regime verdict (green risk-on, red risk-off, amber mixed).
      </p>
    </div>
  );
}
