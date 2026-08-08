// Portfolio-vs-SPY growth-of-$100 lines. Follows RegimeTimeline's pattern:
// ChartContainer owns grid/axis/cursor styling and injects the per-chart
// --color-portfolio / --color-spy variables, and width is measured rather
// than responsive (Recharts' ResponsiveContainer measures 0x0 in jsdom, so
// every geometry assertion would silently blank).
//
// dataviz rules applied: ONE axis (both series are indexed to the same $100
// base, so they share it), 2px lines, an explicit legend because there are
// two series, a crosshair tooltip through ChartTooltipContent, values and
// labels in text tokens (never the series color), and transfer dates as
// ring-outlined dots — a deposit is an event on the line, not a level. The
// ring's hole (and its legend swatch) fills with --card, not --background:
// the chart sits on a card, so --background punches a visibly darker hole in
// dark mode (#09090b inside #18181b).
//
// The two series colors stay bare token references so a palette swap is a
// one-line change: portfolio --chart-1, SPY --muted-foreground dashed
// (dashed + muted reads as the benchmark, subordinate to the book).

import { CartesianGrid, Line, LineChart, ReferenceDot, XAxis, YAxis } from "recharts";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import type { EquityCurvePoint } from "../types";

// The legend and the marker ring live OUTSIDE ChartContainer, where the
// injected --color-portfolio / --color-spy variables are not in scope
// (ChartStyle scopes them to [data-chart=…]) — so the raw tokens are named
// once here and a palette swap stays a one-line change per series.
const PORTFOLIO_COLOR = "var(--chart-1)";
const SPY_COLOR = "var(--muted-foreground)";

const CONFIG = {
  portfolio: { label: "Portfolio", color: PORTFOLIO_COLOR },
  spy: { label: "SPY", color: SPY_COLOR },
} satisfies ChartConfig;

const money = (v: number) => `$${v.toFixed(2)}`;

export interface EquityCurveProps {
  rows: EquityCurvePoint[];
  height?: number;
}

export function EquityCurve({ rows, height = 260 }: EquityCurveProps) {
  const { ref, width } = useMeasuredWidth(640);
  const flows = rows.filter((r) => r.flow !== 0);

  return (
    <div ref={ref} className="equity-curve w-full">
      <ChartContainer
        config={CONFIG}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <LineChart
          width={width}
          height={height}
          data={rows}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
        >
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={32}
            tickFormatter={(d: string) => d.slice(5)}
          />
          <YAxis
            width={44}
            tickLine={false}
            axisLine={false}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `$${Math.round(v)}`}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                valueFormatter={(v) => (typeof v === "number" ? money(v) : "—")}
              />
            }
          />
          <Line
            className="equity-portfolio-line"
            dataKey="portfolio"
            type="monotone"
            stroke="var(--color-portfolio)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            className="equity-spy-line"
            dataKey="spy"
            type="monotone"
            stroke="var(--color-spy)"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          {flows.map((r) => (
            <ReferenceDot
              key={r.date}
              x={r.date}
              y={r.portfolio}
              r={5}
              fill="var(--card)"
              stroke="var(--color-portfolio)"
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ChartContainer>
      <div className="text-muted-foreground mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded" style={{ background: PORTFOLIO_COLOR }} />
          Portfolio
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-0.5 w-4 rounded"
            style={{
              background: `repeating-linear-gradient(90deg, ${SPY_COLOR} 0 4px, transparent 4px 7px)`,
            }}
          />
          SPY
        </span>
        {flows.length > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span
              className="bg-card size-2.5 rounded-full border-2"
              style={{ borderColor: PORTFOLIO_COLOR }}
            />
            deposit/withdrawal (excluded from the portfolio line)
          </span>
        )}
      </div>
    </div>
  );
}
