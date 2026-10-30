// Portfolio-vs-SPY-and-cash growth-of-$100 lines. Follows RegimeTimeline's
// pattern: ChartContainer owns grid/axis/cursor styling and injects the
// per-chart --color-portfolio / --color-spy / --color-cash variables, and
// width is measured rather than responsive (Recharts' ResponsiveContainer
// measures 0x0 in jsdom, so every geometry assertion would silently blank).
//
// dataviz rules applied: ONE axis (all series are indexed to the same $100
// base, so they share it), 2px lines, an explicit legend because there are
// multiple series, a crosshair tooltip through ChartTooltipContent, values
// and labels in text tokens (never the series color). A fill is money
// entering the book, not an event on the line, so nothing is marked.
//
// The series colors stay bare token references so a palette swap is a
// one-line change: portfolio --chart-1, SPY --muted-foreground dashed,
// cash --chart-2 dotted (non-solid + non-primary reads as a benchmark,
// subordinate to the book). Cash is all-or-nothing per data.py: every
// point carries it or none does, so its line and legend render only when
// present — a young fred.db must not leave a dangling legend entry.

import { useInView } from "motion/react";
import type { ReactNode } from "react";
import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis, usePlotArea, useYAxisScale } from "recharts";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import type { EquityCurvePoint } from "../types";

// The legend lives OUTSIDE ChartContainer, where the
// injected --color-portfolio / --color-spy variables are not in scope
// (ChartStyle scopes them to [data-chart=…]) — so the raw tokens are named
// once here and a palette swap stays a one-line change per series.
const PORTFOLIO_COLOR = "var(--chart-1)";
const SPY_COLOR = "var(--muted-foreground)";
const CASH_COLOR = "var(--chart-2)";

const CONFIG = {
  portfolio: { label: "Portfolio", color: PORTFOLIO_COLOR },
  spy: { label: "SPY", color: SPY_COLOR },
  cash: { label: "Cash (DFF)", color: CASH_COLOR },
} satisfies ChartConfig;

const money = (v: number) => `$${v.toFixed(2)}`;

// The band between the book and SPY, split by sign so each half takes its
// tone: `above` spans spy→portfolio where the book leads, `below` spans
// portfolio→spy where it trails; the other half collapses to zero height.
// A pair of range areas, one per sign, is the only way Recharts fills a
// region between two series in two colors.
interface BandRow extends EquityCurvePoint {
  above: [number, number];
  below: [number, number];
}

function withBand(rows: EquityCurvePoint[]): BandRow[] {
  return rows.map((r) => ({
    ...r,
    above: r.portfolio >= r.spy ? [r.spy, r.portfolio] : [r.spy, r.spy],
    below: r.portfolio < r.spy ? [r.portfolio, r.spy] : [r.spy, r.spy],
  }));
}

const LABEL_GAP = 13;

// Where each series ends: its last value beside the line's end, in text
// tokens, pushed apart when two ends are closer than a line of text; and
// a bracket from SPY's end to the book's with the gap in points, only
// when the two ends are far enough apart to fit it.
function EndCaps({ rows, hasCash }: { rows: EquityCurvePoint[]; hasCash: boolean }) {
  const plot = usePlotArea();
  const scale = useYAxisScale();
  const last = rows[rows.length - 1];
  if (!plot || !scale || !last) return null;
  const x0 = plot.x + plot.width + 5;
  const ends = [
    { key: "portfolio", v: last.portfolio, fill: "var(--foreground)", weight: 600 },
    { key: "spy", v: last.spy, fill: "var(--muted-foreground)", weight: 500 },
    ...(hasCash && last.cash !== null ? [{ key: "cash", v: last.cash, fill: "var(--muted-foreground)", weight: 500 }] : []),
  ].map((e) => ({ ...e, y: scale(e.v) as number }));
  const labels = ends.map((e) => ({ ...e, ly: e.y })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].ly - labels[i - 1].ly < LABEL_GAP) labels[i].ly = labels[i - 1].ly + LABEL_GAP;
  }
  const yPort = scale(last.portfolio) as number;
  const ySpy = scale(last.spy) as number;
  const diff = last.portfolio - last.spy;
  const span = Math.abs(ySpy - yPort);
  const bracketX = x0 + 54;
  return (
    <g className="equity-end-caps" aria-hidden="true" fontSize={11} fontFamily="var(--font-mono, ui-monospace, monospace)">
      {labels.map((e) => (
        <text key={e.key} x={x0} y={e.ly} dy={4} fill={e.fill} fontWeight={e.weight}>
          {money(e.v)}
        </text>
      ))}
      {span >= 30 && (
        <g stroke={diff >= 0 ? "var(--tone-up)" : "var(--tone-down)"} strokeWidth={1.5} fill="none">
          <path d={`M${bracketX - 3},${Math.min(yPort, ySpy)} h3 V${Math.max(yPort, ySpy)} h-3`} />
          <text
            x={bracketX + 5}
            y={(yPort + ySpy) / 2}
            dy={4}
            stroke="none"
            fill={diff >= 0 ? "var(--tone-up)" : "var(--tone-down)"}
            fontWeight={600}
          >
            {`${diff >= 0 ? "+" : "−"}${Math.abs(diff).toFixed(1)}`}
          </text>
        </g>
      )}
    </g>
  );
}

// Axis precision follows the plotted span: a 1D window moves a tenth of a
// percent, so whole-dollar ticks would all read "$100". Under a dollar
// shows cents, under five shows tenths, otherwise whole dollars.
function axisDecimals(rows: EquityCurvePoint[]): number {
  let lo = Infinity;
  let hi = -Infinity;
  for (const r of rows) {
    for (const v of [r.portfolio, r.spy, r.cash]) {
      if (v === null) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
  }
  const span = hi - lo;
  return span < 1 ? 2 : span < 5 ? 1 : 0;
}

export interface EquityCurveProps {
  rows: EquityCurvePoint[];
  height?: number;
  // Coverage note ("19 positions · 44 trading days") rendered at the right
  // end of the legend row, at legend size — a footnote, never a headline stat.
  footnote?: ReactNode;
  // Rendered last, under the legend row — Robinhood's order: chart, then
  // the range labels beneath everything. The chart stays agnostic about
  // what the slot holds.
  controls?: ReactNode;
  // Shade the band between the book and SPY (green ahead, red behind).
  gap?: boolean;
  // Label each line's end with its value and bracket the book-vs-SPY gap.
  endLabels?: boolean;
  // Draw every series in from the left, together, the first time the chart
  // scrolls into view; the end labels fade in once the draw lands. CSS in
  // index.css (.equity-curve[data-draw]); nothing under reduced motion.
  draw?: boolean;
}

export function EquityCurve({
  rows,
  height = 260,
  footnote,
  controls,
  gap = false,
  endLabels = false,
  draw = false,
}: EquityCurveProps) {
  const { ref, width } = useMeasuredWidth(640);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const hasCash = rows.some((r) => r.cash !== null);
  const dp = axisDecimals(rows);
  const data = gap ? withBand(rows) : rows;

  return (
    <div ref={ref} className="equity-curve chart-measure w-full" data-draw={draw ? (inView ? "done" : "wait") : undefined}>
      <ChartContainer
        config={CONFIG}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <ComposedChart
          width={width}
          height={height}
          data={data}
          margin={{ top: 8, right: endLabels ? 96 : 12, bottom: 0, left: 0 }}
        >
          <CartesianGrid vertical={false} />
          {gap && (
            <>
              <Area
                className="equity-gap-above"
                dataKey="above"
                type="monotone"
                stroke="none"
                fill="var(--tone-up)"
                fillOpacity={0.16}
                isAnimationActive={false}
                tooltipType="none"
                legendType="none"
              />
              <Area
                className="equity-gap-below"
                dataKey="below"
                type="monotone"
                stroke="none"
                fill="var(--tone-down)"
                fillOpacity={0.16}
                isAnimationActive={false}
                tooltipType="none"
                legendType="none"
              />
            </>
          )}
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={32}
            tickFormatter={(d: string) => d.slice(5)}
          />
          <YAxis
            width={dp === 0 ? 44 : 56}
            tickLine={false}
            axisLine={false}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `$${v.toFixed(dp)}`}
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
            isAnimationActive={false}
          />
          {hasCash && (
            <Line
              className="equity-cash-line"
              dataKey="cash"
              type="monotone"
              stroke="var(--color-cash)"
              strokeWidth={2}
              strokeDasharray="1 3"
              dot={false}
              isAnimationActive={false}
            />
          )}
          {endLabels && <EndCaps rows={rows} hasCash={hasCash} />}
        </ComposedChart>
      </ChartContainer>
      <div className="equity-curve-legend text-muted-foreground mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-0.5 w-4 rounded"
            style={{ background: PORTFOLIO_COLOR }}
          />
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
        {hasCash && (
          <span className="inline-flex items-center gap-1.5">
            <span
              className="h-0.5 w-4 rounded"
              style={{
                background: `repeating-linear-gradient(90deg, ${CASH_COLOR} 0 1.5px, transparent 1.5px 4px)`,
              }}
            />
            Cash (DFF)
          </span>
        )}
        {footnote != null && <span className="ml-auto">{footnote}</span>}
      </div>
      {controls != null && (
        <div className="equity-curve-controls mt-3">{controls}</div>
      )}
    </div>
  );
}
