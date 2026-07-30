// The regime-timeline chart, exactly as the design lab shipped it: a
// full-width VIX AreaChart in the chart token (soft fill, horizontal grid,
// MM-DD ticks) whose per-night dots are colored by that night's regime
// verdict, with the shadcn-style tooltip and a dot-color caption below.
// The old strip + zoom-brush layers are retired (2026-07 redesign).
//
// Width is measured from the container (ResizeObserver) with an explicit
// fallback instead of Recharts' ResponsiveContainer — jsdom measures that
// 0x0, which would silently blank every geometry assertion in tests (see
// KpiSpark's note).

import { useEffect, useRef, useState } from "react";
import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { num } from "../format";
import { tokens } from "../theme";

export interface RegimeTimelineRow {
  date: string;
  regime: string | null;
  vix: number | null;
}

export interface RegimeTimelineProps {
  rows: RegimeTimelineRow[];
  height?: number;
}

const REGIME_COLOR: Record<string, string> = {
  risk_on: tokens.up,
  risk_off: tokens.down,
};

function regimeColor(regime: string | null): string {
  return (regime && REGIME_COLOR[regime]) || tokens.hold;
}

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

/** The lab's shadcn tooltip: date label on top, swatch + series + value. */
function VixTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: RegimeTimelineRow }[];
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="bg-popover text-popover-foreground grid min-w-32 items-start gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{row.date}</div>
      <div className="flex w-full items-center gap-2">
        <div className="size-2.5 shrink-0 rounded-[2px]" style={{ background: "var(--chart-2)" }} />
        <div className="flex flex-1 items-center justify-between gap-4 leading-none">
          <span className="text-muted-foreground">VIX</span>
          <span className="text-foreground font-mono font-medium tabular-nums">
            {num(row.vix, 1)}
          </span>
        </div>
      </div>
    </div>
  );
}

/** Per-night dot colored by that night's regime verdict — the lab design's
 * signature mark on this chart. */
function RegimeDot(props: { cx?: number; cy?: number; payload?: RegimeTimelineRow; index?: number }) {
  const { cx, cy, payload, index } = props;
  if (cx === undefined || cy === undefined || !payload || payload.vix === null) return null;
  return (
    <circle
      key={index}
      className="regime-dot"
      cx={cx}
      cy={cy}
      r={4}
      fill={regimeColor(payload.regime)}
      stroke={tokens.ink}
      strokeWidth={1.5}
    />
  );
}

export function RegimeTimeline({ rows, height = 208 }: RegimeTimelineProps) {
  const { ref, width } = useMeasuredWidth(640);

  if (rows.length === 0) {
    return <p className="empty">no data</p>;
  }

  return (
    <div ref={ref} className="regime-timeline w-full">
      <AreaChart
        width={width}
        height={height}
        data={rows}
        margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
      >
        <CartesianGrid vertical={false} stroke={tokens.edge} />
        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          tick={{ fill: tokens.muted, fontSize: 11 }}
          tickFormatter={(d: string) => d.slice(5)}
        />
        <YAxis
          type="number"
          domain={["auto", "auto"]}
          width={32}
          tickLine={false}
          axisLine={false}
          tick={{ fill: tokens.muted, fontSize: 11 }}
        />
        <Tooltip content={<VixTooltip />} cursor={{ stroke: tokens.edge }} />
        <Area
          className="regime-vix-line"
          type="monotone"
          dataKey="vix"
          stroke="var(--chart-2)"
          strokeWidth={2}
          fill="var(--chart-2)"
          fillOpacity={0.12}
          dot={<RegimeDot />}
          isAnimationActive={false}
          connectNulls
        />
      </AreaChart>
      <p className="text-muted-foreground mt-2 text-xs">
        Dot color = that night's regime verdict (green risk-on, red risk-off, amber mixed).
      </p>
    </div>
  );
}
