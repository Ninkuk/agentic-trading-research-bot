// Regime history: two synced layers over the same nightly rows.
//   (a) a strip — one HTML cell per night, colored by that night's regime
//       (tokens.up/down for the two poles, tokens.hold for anything else —
//       a neutral-gray midpoint, never a third hue, per the dataviz
//       diverging-mark rule).
//   (b) a Recharts VIX LineChart with a Brush for zoom.
// Recharts' Brush already restricts the line's own visible window; the
// strip doesn't get that for free, so its window is lifted into state via
// Brush.onChange and applied by slicing `rows` ourselves.
// No ResponsiveContainer — see Sparkline's note; charts take explicit
// width/height.

import { useMemo, useState } from "react";
import { Brush, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { dateShort, num } from "../format";
import { tokens } from "../theme";

export interface RegimeTimelineRow {
  date: string;
  regime: string | null;
  vix: number | null;
}

export interface RegimeTimelineProps {
  rows: RegimeTimelineRow[];
  width?: number;
  height?: number;
}

const REGIME_COLOR: Record<string, string> = {
  risk_on: tokens.up,
  risk_off: tokens.down,
};

function regimeColor(regime: string | null): string {
  return (regime && REGIME_COLOR[regime]) || tokens.hold;
}

function cellTitle(row: RegimeTimelineRow): string {
  return `${row.date} · ${row.regime ?? "unknown"} · VIX ${num(row.vix, 1)}`;
}

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
    <div className="spark-tooltip">
      {dateShort(row.date)}: VIX {num(row.vix, 1)}
    </div>
  );
}

export function RegimeTimeline({ rows, width = 640, height = 200 }: RegimeTimelineProps) {
  const lastIndex = Math.max(rows.length - 1, 0);
  const [range, setRange] = useState({ startIndex: 0, endIndex: lastIndex });

  // rows can grow between renders (a fresh export); clamp so a stale
  // endIndex from a shorter prior array never slices past the new end.
  const clampedEnd = Math.min(range.endIndex, lastIndex);
  const visible = useMemo(
    () => rows.slice(range.startIndex, clampedEnd + 1),
    [rows, range.startIndex, clampedEnd],
  );

  if (rows.length === 0) {
    return <p className="empty">no data</p>;
  }

  return (
    <div className="regime-timeline">
      <div
        className="stripwrap"
        role="img"
        aria-label={`regime by night, ${visible[0]?.date} to ${visible[visible.length - 1]?.date}`}
      >
        <div className="strip">
          {visible.map((row, i) => (
            <div
              key={`${row.date}-${i}`}
              className="strip-cell"
              style={{ backgroundColor: regimeColor(row.regime) }}
              title={cellTitle(row)}
            />
          ))}
        </div>
      </div>
      <LineChart
        width={width}
        height={height}
        data={rows}
        margin={{ top: 8, right: 8, bottom: 4, left: 8 }}
      >
        <XAxis dataKey="date" hide />
        <YAxis type="number" domain={["auto", "auto"]} hide />
        <Tooltip content={<VixTooltip />} cursor={{ stroke: tokens.edge }} />
        <Line
          className="regime-vix-line"
          type="monotone"
          dataKey="vix"
          stroke={tokens.hold}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          connectNulls
        />
        <Brush
          dataKey="date"
          height={20}
          travellerWidth={8}
          stroke={tokens.brass}
          fill={tokens.gutter}
          startIndex={range.startIndex}
          endIndex={clampedEnd}
          onChange={({ startIndex, endIndex }) => setRange({ startIndex, endIndex })}
        />
      </LineChart>
    </div>
  );
}
