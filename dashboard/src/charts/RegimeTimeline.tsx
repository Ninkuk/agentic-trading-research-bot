// The regime-timeline chart, verbatim from the design lab's
// RegimeTimelineChart: a full-width VIX AreaChart inside ChartContainer
// (which owns the grid/axis/cursor styling via its CSS hooks and injects
// the per-chart --color-vix variable), per-night dots colored by that
// night's regime verdict (the lab's exact hexes), the shadcn
// ChartTooltipContent, and the dot-color caption below.
//
// The one deviation from the lab file: width. The lab used
// ResponsiveContainer ("aspect-auto w-full"); jsdom measures that 0x0 and
// every geometry assertion in tests silently blanks, so this measures the
// container itself (ResizeObserver, explicit fallback) and passes
// responsive={false} — pixel-identical in a real browser.

import { useEffect, useRef, useState } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
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

// The lab's dot palette — fixed hexes, same in both themes.
const REGIME_DOT: Record<string, string> = {
  risk_on: "#10b981",
  risk_off: "#ef4444",
  mixed: "#f59e0b",
};

const vixConfig = { vix: { label: "VIX", color: "var(--chart-2)" } } satisfies ChartConfig;

function useMeasuredWidth(fallback: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const apply = () => {
      if (el.clientWidth > 0) setWidth(el.clientWidth);
    };
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    apply();
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

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
