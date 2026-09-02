// oxlint-disable react/only-export-components -- pure formatting helpers
// that return JSX; there is no component here for fast refresh to preserve.
//
// The ONE default cell formatter, keyed on column name: hit_rate + CI →
// RangeCell, excess keys → DivergingCell, weight/heat → BarCell (both
// scaled to the column max, so `makeSectionCell(rows)` precomputes it;
// bare `sectionCell` knows no max and keeps the digits), fractions →
// percents, dollars → usd(), verdicts/recommendations → tinted pills,
// booleans → pills by key semantics, symbols → mono, the rest → formatCell.

import type { ReactNode } from "react";
import { pct, signed, usd } from "../format";
import type { Column, Row } from "../types";
import { Badge } from "../components/ui/badge";
import { formatCell, humanizeId, isMachineId } from "./formatCell";
import { Sparkline } from "./Sparkline";
import { BarCell } from "./marks/BarCell";
import { DivergingCell } from "./marks/DivergingCell";
import { RangeCell } from "./marks/RangeCell";
import { isFiniteNumber, maxAbs } from "./marks/geometry";

// Fractions of 1 → percent (0.58 → 58%).
const PCT_FRACTION = new Set([
  "coverage",
  "hit_rate",
  "hit_ci_lo",
  "hit_ci_hi",
  "null_rate",
  "avg_excess",
  "baseline",
  "p_up",
  "p_down",
  "short_ratio",
  "net_margin",
  "roe",
]);
// Signed fractions → signed tinted percent (+1.8% / −0.6%).
const PCT_SIGNED = new Set([
  "avg_dir_excess",
  "avg_directional_excess",
  "avg_fwd_return",
  "avg_bench_return",
  "min_bench_return",
  "max_bench_return",
  "fwd_return",
  "bench_fwd_return",
  "excess",
  "dir_excess",
  "premium_return",
]);
// Already expressed in percent units (advisor heat, exit advice).
const PCT_UNIT = new Set(["heat_pct", "weight_pct", "unrealized_pct", "stop_distance_pct"]);
const DOLLARS = new Set([
  "heat_dollars",
  "cap_dollars",
  "market_value",
  "price",
  "prev_close",
  "close",
  "pnl_dollars",
  "avg_cost",
  "stop_price",
  "limit_price",
  "ref_price",
  "entry_close",
  "notional",
]);
// Boolean flags render as a tinted pill; the variant says whether `true`
// is the good state (a beaten benchmark) or the bad one (a stale ATR) —
// text stays the primary channel, the tint only agrees with it.
const BOOL_GOOD = new Set(["verdict_correct", "beat_benchmark", "beats_baseline", "aligned"]);
const BOOL_BAD = new Set([
  "anti_signal",
  "falling_knife",
  "strong",
  "atr_stale",
  "uncovered",
  "short_leg",
  "extreme",
  "inverted",
]);
// Symbols stay mono; signal ids and reopen triggers are no longer here —
// they humanize into words (see the branches in sectionCell below), and
// words are sans per the Mono-Numbers Rule.
const MONO = new Set(["symbol", "ticker", "symbols"]);
// Column-scaled marks: a diverging bar needs the table's max |excess|, a
// magnitude bar its max weight/heat. Without a scale the digits stand alone.
const DIVERGING = new Set(["avg_directional_excess", "avg_dir_excess", "excess", "avg_excess", "dir_excess"]);
const BAR_FORMAT: Record<string, (v: number) => string> = {
  weight_pct: (v) => pct(v, 2),
  heat_pct: (v) => pct(v, 2),
  heat_dollars: usd,
};

export type ColumnScale = ReadonlyMap<string, number>;

export function columnScale(rows: Row[]): ColumnScale {
  const scale = new Map<string, number>();
  for (const key of [...DIVERGING, ...Object.keys(BAR_FORMAT)]) {
    const max = maxAbs(rows.map((r) => r[key]));
    if (max !== null) scale.set(key, max);
  }
  return scale;
}

function firstNumber(...candidates: unknown[]): number | undefined {
  return candidates.find(isFiniteNumber);
}

export function signedPctCell(v: unknown): ReactNode {
  if (typeof v !== "number") return "—";
  const cls = v > 0 ? "tag-on" : v < 0 ? "tag-off" : undefined;
  return <span className={cls}>{signed(v * 100, 1)}%</span>;
}

export function scoreCell(v: unknown): ReactNode {
  if (typeof v !== "number") return "—";
  return <span className={`font-semibold ${v < 0 ? "tag-off" : "tag-on"}`}>{signed(v, 0)}</span>;
}

const REC_VARIANT: Record<string, "up" | "down" | "hold"> = {
  keep: "up",
  watch: "hold",
  "anti-signal": "down",
  anti: "down",
};

// Research verdicts get the same tone treatment as every other verdict on
// the page — SOUND/FLAWED as bare uppercase text made a failed thesis
// visually identical to a sound one (the Three-Tones Rule, unapplied).
const RESEARCH_VERDICT_VARIANT: Record<string, "up" | "down" | "hold"> = {
  SOUND: "up",
  FLAWED: "down",
  UNPROVEN: "hold",
};

export function researchVerdictPill(v: unknown): ReactNode {
  if (typeof v !== "string" || !v) return "—";
  const variant = RESEARCH_VERDICT_VARIANT[v.toUpperCase()];
  if (!variant) return formatCell(v);
  return <Badge variant={variant}>{v}</Badge>;
}

export function recommendationPill(v: unknown): ReactNode {
  const text = typeof v === "string" && v ? v : "insufficient evidence";
  return (
    <Badge variant={REC_VARIANT[text] ?? "secondary"} className={`rec rec--${REC_VARIANT[text] ?? "ins"}`}>
      {text}
    </Badge>
  );
}

/** hit_rate with its CI folded in as a whisker; the rate the signal must
 * beat (null rate, else drift/plain baseline) draws as the dashed tick. */
export function hitRateCell(row: Row): ReactNode {
  return (
    <RangeCell
      rate={row.hit_rate}
      lo={row.hit_ci_lo}
      hi={row.hit_ci_hi}
      tick={firstNumber(row.null_rate, row.drift_baseline, row.baseline)}
    />
  );
}

/** CI columns fold into the hit-rate cell — sections whose column set
 * includes them should drop these from their DataTable columns. */
export const HIDDEN_CI_KEYS = new Set(["via_crosswalk", "hit_ci_lo", "hit_ci_hi"]);

export function visibleColumns(columns: Column[]): Column[] {
  return columns.filter((c) => !HIDDEN_CI_KEYS.has(c.key));
}

/** Machine ids render as words with the raw id preserved in a title
 * attribute; reopen triggers additionally drop a leading ticker prefix
 * ("bsy-q2-print…" in a row whose Ticker column already says BSY). */
export function machineIdCell(row: Row, key: string, v: unknown): ReactNode {
  if (typeof v !== "string" || !v) return formatCell(v as never);
  let slug = v;
  if (key === "trigger") {
    const ticker = typeof row.ticker === "string" ? row.ticker.toLowerCase() : null;
    if (ticker && slug.toLowerCase().startsWith(`${ticker}-`)) {
      slug = slug.slice(ticker.length + 1);
    }
  }
  if (!isMachineId(slug)) return slug;
  return <span title={v}>{humanizeId(slug)}</span>;
}

/** The generic per-cell dispatcher — the lab's buildRenderers, flattened. */
export function boolCell(key: string, v: unknown): ReactNode {
  if (typeof v !== "boolean") return "—";
  if (BOOL_GOOD.has(key))
    return (
      <Badge variant={v ? "up" : "down"} className={`bool bool--${v ? "good" : "bad"}`}>
        {v ? "yes" : "no"}
      </Badge>
    );
  if (BOOL_BAD.has(key))
    return v ? (
      <Badge variant="down" className="bool bool--bad">
        yes
      </Badge>
    ) : (
      "no"
    );
  return v ? "yes" : "no";
}

function scaledCell(row: Row, col: Column, scale: ColumnScale): ReactNode {
  const k = col.key;
  const v = row[k];
  if (Array.isArray(v)) return <Sparkline values={v} label={col.label} />;
  if (typeof v === "boolean" && k !== "in_portfolio" && k !== "exceeds_buying_power")
    return boolCell(k, v);
  if (k === "signal_id" || k === "trigger") return machineIdCell(row, k, v);
  if (k === "verdict") return researchVerdictPill(v);
  if (k === "score_sum") return scoreCell(v);
  if (k === "recommendation") return recommendationPill(v);
  if (k === "hit_rate") return hitRateCell(row);
  const max = scale.get(k);
  if (max !== undefined && DIVERGING.has(k)) return <DivergingCell value={v} max={max} />;
  if (max !== undefined && k in BAR_FORMAT) return <BarCell value={v} max={max} format={BAR_FORMAT[k]} />;
  if (k === "in_portfolio") return v === true ? <Badge variant="outline">held</Badge> : null;
  if (k === "exceeds_buying_power")
    return v === true ? <Badge variant="destructive">over BP</Badge> : "—";
  if (k === "worst_staleness_days")
    return typeof v === "number" ? `${formatCell(v)}d` : formatCell(v);
  if (PCT_FRACTION.has(k)) return typeof v === "number" ? pct(v * 100, 0) : formatCell(v);
  if (PCT_SIGNED.has(k)) return signedPctCell(v);
  if (PCT_UNIT.has(k)) return typeof v === "number" ? pct(v, 2) : formatCell(v);
  if (DOLLARS.has(k)) return typeof v === "number" ? usd(v) : formatCell(v);
  if (MONO.has(k)) return <span className="font-mono font-medium">{formatCell(v)}</span>;
  return formatCell(v);
}

/** Build the cell renderer for one table: the column maxima the diverging
 * and magnitude bars scale against come from these rows. */
export function makeSectionCell(rows: Row[]): (row: Row, col: Column) => ReactNode {
  const scale = columnScale(rows);
  return (row, col) => scaledCell(row, col, scale);
}

/** Scale-free renderer: every scaled key keeps its digits. */
export const sectionCell = makeSectionCell([]);
