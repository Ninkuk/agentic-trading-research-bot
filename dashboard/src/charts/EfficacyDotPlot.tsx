// A signal-efficacy row's hit-rate readout: point estimate + 95% CI
// whisker against a gray reference band at the null rate — the do-nothing
// base rate a signal must beat to be worth anything. Ported from the
// static page's `dot_ci_svg` (deploy/launchd/dashboard_lib/svg.py), now
// hand-drawn SVG (not a full Recharts chart — this is a tiny inline table
// cell, and hand-computing the linear scale keeps the whisker coordinates
// exactly the ones a test can assert on). The dot only wears the accent
// (tokens.up) when the WHOLE CI clears the baseline (ci_lo > null_rate) —
// the "keep" emphasis form; otherwise both dot and whisker stay neutral
// gray. Same NULL contract as the old `_ci_bar`: any of hit_rate/ci_lo/
// ci_hi missing degrades to a plain dash.

import { pct } from "../format";
import { tokens } from "../theme";

export interface EfficacyRow {
  hit_rate: number | null;
  hit_ci_lo: number | null;
  hit_ci_hi: number | null;
  null_rate: number | null;
}

export interface EfficacyDotPlotProps {
  row: EfficacyRow;
  width?: number;
  height?: number;
}

const INSET = 4;
const BAND_WIDTH = 3;

function px(frac: number, width: number): number {
  const clamped = Math.max(0, Math.min(frac, 1));
  return Math.round((clamped * (width - INSET * 2) + INSET) * 10) / 10;
}

export function EfficacyDotPlot({ row, width = 160, height = 20 }: EfficacyDotPlotProps) {
  const { hit_rate, hit_ci_lo, hit_ci_hi, null_rate } = row;
  if (hit_rate === null || hit_ci_lo === null || hit_ci_hi === null) {
    return <div className="ci">—</div>;
  }

  const mid = height / 2;
  const loX = px(hit_ci_lo, width);
  const hiX = px(hit_ci_hi, width);
  const dotX = px(hit_rate, width);
  const clearsBaseline = null_rate !== null && hit_ci_lo > null_rate;
  const dotColor = clearsBaseline ? tokens.up : tokens.hold;
  const label =
    `best estimate ${pct(hit_rate * 100, 0)}, ` +
    `95% range ${pct(hit_ci_lo * 100, 0)}–${pct(hit_ci_hi * 100, 0)}`;

  return (
    <div className="ci">
      <div className="num">
        <b>{pct(hit_rate * 100, 0)}</b>
      </div>
      <svg role="img" viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
        <title>{label}</title>
        <line
          className="dot-track"
          x1={INSET}
          y1={mid}
          x2={width - INSET}
          y2={mid}
          stroke={tokens.edge}
          strokeWidth={1}
        />
        {null_rate !== null && (
          <rect
            className="dot-baseline-band"
            x={px(null_rate, width) - BAND_WIDTH / 2}
            y={2}
            width={BAND_WIDTH}
            height={height - 4}
            fill={tokens.hold}
          />
        )}
        <line
          className="dot-whisker"
          x1={loX}
          y1={mid}
          x2={hiX}
          y2={mid}
          stroke={tokens.hold}
          strokeWidth={2}
        />
        <circle
          className="dot-mark"
          cx={dotX}
          cy={mid}
          r={4}
          fill={dotColor}
          stroke={tokens.ink}
          strokeWidth={1}
        />
      </svg>
    </div>
  );
}
