// oxlint-disable react/only-export-components -- pure formatting helpers
// that return JSX; there is no component here for fast refresh to preserve.
//
// The design-lab SectionBlock's column-key formatting heuristics, shipped
// as the ONE default cell formatter: fraction columns → percents, signed
// excess/return fractions → tinted signed percents, advisor dollar/percent
// columns → usd()/pct(), score_sum → tinted signed, recommendation/verdict
// → tinted pills, in_portfolio → a held pill, exceeds_buying_power → a
// destructive pill, staleness → "Nd", symbol-ish columns → mono. Everything
// else falls through to formatCell. A brand-new exporter section gets a
// sane rendering with no frontend change.

import type { ReactNode } from "react";
import { pct, signed, usd } from "../format";
import type { Column, Row } from "../types";
import { Badge } from "../components/ui/badge";
import { formatCell, humanizeId, isMachineId } from "./formatCell";

// Fractions of 1 → percent (0.58 → 58%).
const PCT_FRACTION = new Set(["coverage", "hit_rate", "hit_ci_lo", "hit_ci_hi", "null_rate", "avg_excess"]);
// Signed fractions → signed tinted percent (+1.8% / −0.6%).
const PCT_SIGNED = new Set([
  "avg_dir_excess",
  "avg_directional_excess",
  "avg_fwd_return",
  "avg_bench_return",
  "min_bench_return",
  "max_bench_return",
]);
// Already expressed in percent units (advisor heat).
const PCT_UNIT = new Set(["heat_pct", "weight_pct"]);
const DOLLARS = new Set(["heat_dollars", "cap_dollars", "market_value", "price", "prev_close", "close"]);
// Symbols stay mono; signal ids and reopen triggers are no longer here —
// they humanize into words (see the branches in sectionCell below), and
// words are sans per the Mono-Numbers Rule.
const MONO = new Set(["symbol", "ticker", "symbols"]);

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

/** hit_rate with its CI folded in when the row carries ci columns — the CI
 * stacks in a muted line under the rate so the merged cell stays as narrow
 * as a plain percent and can't crowd its left neighbor (lab round 4). */
export function hitRateCell(row: Row): ReactNode {
  const rate = typeof row.hit_rate === "number" ? pct(row.hit_rate * 100, 0) : "—";
  const lo = row.hit_ci_lo;
  const hi = row.hit_ci_hi;
  if (typeof lo !== "number" || typeof hi !== "number") return rate;
  return (
    <span className="inline-flex flex-col items-end leading-tight">
      <span>{rate}</span>
      <span className="text-muted-foreground text-xs">
        CI {Math.round(lo * 100)}–{Math.round(hi * 100)}
      </span>
    </span>
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
export function sectionCell(row: Row, col: Column): ReactNode {
  const k = col.key;
  const v = row[k];
  if (k === "signal_id" || k === "trigger") return machineIdCell(row, k, v);
  if (k === "verdict") return researchVerdictPill(v);
  if (k === "score_sum") return scoreCell(v);
  if (k === "recommendation") return recommendationPill(v);
  if (k === "hit_rate") return hitRateCell(row);
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
