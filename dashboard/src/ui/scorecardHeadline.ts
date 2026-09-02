// Headline numbers lifted from the trader-scorecard `text_lines` report
// (scorer/scorecard.py `build_report`). Blocks are matched by heading
// prefix and columns by name, never by position — the alignment block's
// columns have already been renamed once (aligned=1/0 → agreed/contrarian).

export interface ScorecardHeadline {
  /** "Portfolio vs SPY" inception row, in percent points. */
  twr: { portfolio: number; spy: number; excess: number } | null;
  /** Best passed_inferred avg_dir_excess (raw fraction) and its horizon. */
  filterEdge: { horizon: number; excess: number } | null;
  /** avg_entry_slippage in percent points (identical across horizons). */
  slippage: number | null;
  alignment: { horizon: number; agreed: number; contrarian: number } | null;
}

interface Block {
  heading: string;
  columns: string[];
  rows: string[][];
}

function blocks(lines: string[]): Block[] {
  const out: Block[] = [];
  let cur: string[] = [];
  const flush = () => {
    if (cur.length === 0) return;
    const pipes = cur.slice(1).filter((l) => l.includes("|"));
    if (pipes.length >= 2) {
      const split = (l: string) => l.split("|").map((c) => c.trim());
      out.push({ heading: cur[0].trim(), columns: split(pipes[0]), rows: pipes.slice(1).map(split) });
    }
    cur = [];
  };
  for (const line of lines) {
    if (line.trim() === "") flush();
    else if (!/^=+.*=+$/.test(line.trim())) cur.push(line);
  }
  flush();
  return out;
}

function find(all: Block[], prefix: RegExp): Block | undefined {
  return all.find((b) => prefix.test(b.heading));
}

function col(b: Block, name: RegExp): number {
  return b.columns.findIndex((c) => name.test(c));
}

/** "3.01%" → 3.01, "-0.0723" → -0.0723; prose ("insufficient data") → null. */
function numeric(s: string | undefined): number | null {
  if (s === undefined) return null;
  const m = /^(-?\d+(?:\.\d+)?)%?$/.exec(s.trim());
  return m ? Number(m[1]) : null;
}

function pickHorizon(rows: string[][], hi: number, want: number): string[] | undefined {
  const exact = rows.find((r) => numeric(r[hi]) === want);
  if (exact) return exact;
  return rows
    .filter((r) => numeric(r[hi]) !== null)
    .sort((a, b) => numeric(a[hi])! - numeric(b[hi])!)[0];
}

export function parseScorecardHeadline(lines: string[]): ScorecardHeadline | null {
  const all = blocks(lines);
  const h: ScorecardHeadline = { twr: null, filterEdge: null, slippage: null, alignment: null };

  const twr = find(all, /^Portfolio vs SPY/i);
  if (twr) {
    const w = col(twr, /^window$/i);
    const p = col(twr, /portfolio/i);
    const s = col(twr, /^SPY$/i);
    const e = col(twr, /^excess$/i);
    const row = twr.rows.find((r) => r[w] === "inception");
    if (row && p >= 0 && s >= 0 && e >= 0) {
      const portfolio = numeric(row[p]);
      const spy = numeric(row[s]);
      const excess = numeric(row[e]);
      if (portfolio !== null && spy !== null && excess !== null) h.twr = { portfolio, spy, excess };
    }
  }

  const edge = find(all, /^Filter edge/i);
  if (edge) {
    const hi = col(edge, /^horizon$/i);
    const resp = col(edge, /^response$/i);
    const ex = col(edge, /avg_dir_excess/i);
    if (hi >= 0 && resp >= 0 && ex >= 0) {
      for (const r of edge.rows) {
        if (r[resp] !== "passed_inferred") continue;
        const v = numeric(r[ex]);
        const horizon = numeric(r[hi]);
        if (v === null || horizon === null) continue;
        if (h.filterEdge === null || v > h.filterEdge.excess) h.filterEdge = { horizon, excess: v };
      }
    }
  }

  const cost = find(all, /^Execution cost/i);
  if (cost) {
    const sl = col(cost, /avg_entry_slippage/i);
    if (sl >= 0) h.slippage = cost.rows.map((r) => numeric(r[sl])).find((v) => v !== null) ?? null;
  }

  const align = find(all, /^Alignment/i);
  if (align) {
    const hi = col(align, /^horizon$/i);
    const ag = col(align, /^(agreed|aligned=1)$/i);
    const co = col(align, /^(contrarian|aligned=0)$/i);
    const row = hi >= 0 ? pickHorizon(align.rows, hi, 5) : undefined;
    if (row && ag >= 0 && co >= 0) {
      const agreed = numeric(row[ag]);
      const contrarian = numeric(row[co]);
      const horizon = numeric(row[hi]);
      if (agreed !== null && contrarian !== null && horizon !== null)
        h.alignment = { horizon, agreed, contrarian };
    }
  }

  return h.twr || h.filterEdge || h.slippage !== null || h.alignment ? h : null;
}
