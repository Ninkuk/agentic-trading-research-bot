// A tile-scoped trend line: 2px, no axes/legend (the tile's own label
// names the series), crosshair tooltip on hover. Degrades to nothing for
// fewer than 2 usable points — the ported `_sparkline`/`tile_spark` rule
// (deploy/launchd/dashboard_lib/svg.py) carried over from the static page.
// No ResponsiveContainer: jsdom measures it 0x0, so every geometry
// assertion (including the ones in this file's tests) would silently fail.
// Callers size the tile; we take explicit width/height.

import { Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { dateShort, num } from "../format";
import { tokens } from "../theme";

export interface SparklinePoint {
  date: string;
  value: number | null;
}

export type SparklineTone = "up" | "down" | "hold";

export interface SparklineProps {
  points: SparklinePoint[];
  width?: number;
  height?: number;
  tone?: SparklineTone;
}

function SparklineTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SparklinePoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="spark-tooltip">
      {dateShort(point.date)}: {num(point.value)}
    </div>
  );
}

export function Sparkline({ points, width = 120, height = 32, tone = "hold" }: SparklineProps) {
  const usable = points.filter((p) => p.value !== null);
  if (usable.length < 2) return null;

  const color = tokens[tone];

  return (
    <LineChart
      width={width}
      height={height}
      data={usable}
      margin={{ top: 4, right: 4, bottom: 4, left: 4 }}
    >
      <XAxis dataKey="date" type="category" hide />
      <YAxis type="number" domain={["auto", "auto"]} hide />
      <Tooltip content={<SparklineTooltip />} cursor={{ stroke: tokens.edge }} />
      <Line
        className="spark-line"
        type="monotone"
        dataKey="value"
        stroke={color}
        strokeWidth={2}
        dot={false}
        isAnimationActive={false}
        connectNulls
      />
    </LineChart>
  );
}
