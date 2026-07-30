// KPI sparkline for the summary card: a small area chart over a tile's
// history with the shadcn tooltip floating ABOVE the mark (the tooltip is
// larger than the chart, so inside the viewbox it would cover the line it
// describes). Hidden YAxis with data-driven domain — without it Recharts
// baselines the area at 0 and a series hovering around 14 renders as a
// solid filled box. Degrades to nothing under 2 usable points, like
// Sparkline. Explicit width/height (no ResponsiveContainer): jsdom measures
// it 0x0 and every geometry assertion would silently fail.

import { Area, AreaChart, Tooltip, XAxis, YAxis } from "recharts";
import { dateShort, num } from "../format";

export interface KpiSparkPoint {
  date: string;
  value: number | null;
}

export interface KpiSparkProps {
  label: string;
  points: KpiSparkPoint[];
  width?: number;
  height?: number;
}

function KpiSparkTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { payload: KpiSparkPoint }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="spark-tooltip">
      {dateShort(label ?? point.date)} · {num(point.value)}
    </div>
  );
}

export function KpiSpark({ label, points, width = 96, height = 36 }: KpiSparkProps) {
  const usable = points.filter((p) => p.value !== null);
  if (usable.length < 2) return null;
  return (
    <AreaChart
      width={width}
      height={height}
      data={usable}
      margin={{ top: 2, right: 0, bottom: 0, left: 0 }}
      aria-label={`${label} history`}
    >
      <XAxis dataKey="date" hide />
      <YAxis hide domain={["dataMin", "dataMax"]} />
      <Tooltip
        content={<KpiSparkTooltip />}
        allowEscapeViewBox={{ x: true, y: true }}
        position={{ y: -34 }}
        wrapperStyle={{ zIndex: 20 }}
      />
      <Area
        type="monotone"
        dataKey="value"
        stroke="var(--chart-2)"
        strokeWidth={1.5}
        fill="var(--chart-2)"
        fillOpacity={0.15}
        dot={false}
        isAnimationActive={false}
      />
    </AreaChart>
  );
}
