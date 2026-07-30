// A scorecard row's net vote: a diverging bar around a zero baseline (left
// = bearish/tokens.down, right = bullish/tokens.up) plus the signed number
// as text — color is never the only channel a colorblind or grayscale
// reader has. Ported from the static page's `.scorecell`/`.sbar` markup
// (deploy/launchd/dashboard_lib/sections.py's `_score_cell`), now driven by
// inline token colors instead of the `--mark-up`/`--mark-down` custom
// properties so the palette is testable straight off the rendered element.

import { signed } from "../format";
import { tokens } from "../theme";

export interface ScoreBarProps {
  value: number;
  bullish: number;
  bearish: number;
  max: number;
  width?: number;
}

export function ScoreBar({ value, bullish, bearish, max, width = 88 }: ScoreBarProps) {
  const positive = value >= 0;
  const denom = max > 0 ? max : 1;
  const fillPct = Math.min(Math.abs(value) / denom, 1) * 50; // % of the full track (half each side)

  return (
    <div className="scorecell">
      <span className={`sval ${positive ? "up" : "down"}`}>{signed(value, 0)}</span>
      <div className="sbar" style={{ width }} title={`${bullish} bullish, ${bearish} bearish`}>
        <i
          className={`score-bar-mark ${positive ? "p" : "n"}`}
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: positive ? "50%" : undefined,
            right: positive ? undefined : "50%",
            width: `${fillPct}%`,
            backgroundColor: positive ? tokens.up : tokens.down,
            borderRadius: positive ? "0 4px 4px 0" : "4px 0 0 4px",
          }}
        />
      </div>
    </div>
  );
}
