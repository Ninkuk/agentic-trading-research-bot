// The per-ticker drill-down route (#/ticker/SYM): header (symbol, back
// link, pin toggle) -> score-history chart -> signal breakdown table ->
// research verdicts list -> journal fills table + position card when held.
// Each body block degrades independently when its backing array/object is
// empty or missing — a ticker with signals but no fills still shows its
// signals. A symbol absent from `doc.tickers` (not in tonight's scorecard,
// holdings, or journal) gets an honest message instead of four guessed-at
// empty blocks; the header still renders so the symbol can still be pinned
// even though there's nothing to show below it.
//
// Pins are the single `usePrefs("pins", [])` list shared with Scorecard's
// `pinnedFirst` — toggling here and pinning a scorecard row both write the
// same key, so the two views never disagree about what's pinned.

import { Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import { REPO_URL } from "../constants";
import { dateShort, num, pct, signed, usd } from "../format";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import { usePrefs } from "../hooks/usePrefs";
import { tokens } from "../theme";
import type { Column, DashboardDoc, Row, ScoreHistoryPoint, TickerPosition } from "../types";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import { DataTable } from "../ui/DataTable";

export interface TickerDetailProps {
  doc: DashboardDoc;
  symbol: string;
}

const SIGNAL_COLUMNS: Column[] = [
  { key: "signal", label: "Signal", numeric: false, direction: null, term: null },
  { key: "score", label: "Score", numeric: true, direction: null, term: null },
  { key: "raw_value", label: "Raw value", numeric: true, direction: null, term: null },
];

const FILL_COLUMNS: Column[] = [
  { key: "fill_date", label: "Fill date", numeric: false, direction: null, term: null },
  { key: "action", label: "Action", numeric: false, direction: null, term: null },
  { key: "side", label: "Side", numeric: false, direction: null, term: null },
  { key: "fill_price", label: "Fill price", numeric: true, direction: null, term: null },
  { key: "quantity", label: "Qty", numeric: true, direction: null, term: null },
  { key: "exit_fill_date", label: "Exit date", numeric: false, direction: null, term: null },
  { key: "exit_fill_price", label: "Exit price", numeric: true, direction: null, term: null },
  { key: "opinion_score_sum", label: "Opinion score", numeric: true, direction: null, term: null },
];

function ScoreDot(props: { cx?: number; cy?: number; payload?: ScoreHistoryPoint }) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload || payload.score_sum === null) return null;
  const color = payload.score_sum > 0 ? tokens.up : payload.score_sum < 0 ? tokens.down : tokens.hold;
  return <circle className="score-dot" cx={cx} cy={cy} r={4} fill={color} stroke={tokens.ink} strokeWidth={1} />;
}

const scoreConfig = {
  score_sum: { label: "Score", color: "var(--chart-2)" },
} satisfies ChartConfig;

function ScoreHistoryChart({ points }: { points: ScoreHistoryPoint[] }) {
  const { ref, width } = useMeasuredWidth(560);
  const usable = points.filter((p) => p.score_sum !== null);
  if (usable.length < 2) {
    return <p className="empty">no score history yet</p>;
  }
  return (
    <div ref={ref} className="w-full">
      <ChartContainer
        config={scoreConfig}
        responsive={false}
        className="aspect-auto w-full"
        style={{ height: 180 }}
      >
        <LineChart width={width} height={180} data={usable} margin={{ top: 12, right: 16, bottom: 0, left: 0 }}>
          <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} tickFormatter={dateShort} />
          <YAxis type="number" domain={["auto", "auto"]} allowDecimals={false} width={28} tickLine={false} axisLine={false} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(l) => dateShort(String(l))}
                valueFormatter={(v) => (typeof v === "number" ? signed(v, 0) : String(v))}
              />
            }
          />
          <ReferenceLine y={0} stroke={tokens.edge} />
          <Line
            className="score-history-line"
            type="monotone"
            dataKey="score_sum"
            stroke="var(--color-score_sum)"
            strokeWidth={2}
            dot={<ScoreDot />}
            isAnimationActive={false}
            connectNulls
          />
        </LineChart>
      </ChartContainer>
    </div>
  );
}

function PositionCard({ position }: { position: TickerPosition }) {
  return (
    <div className="tiles position-card">
      <div className="tile">
        <div className="v">{num(position.quantity, 0)}</div>
        <div className="k">Quantity</div>
      </div>
      <div className="tile">
        <div className="v">{usd(position.market_value)}</div>
        <div className="k">Market value</div>
      </div>
      <div className="tile">
        <div className="v">{usd(position.heat_dollars)}</div>
        <div className="k">Heat $</div>
      </div>
      <div className="tile">
        <div className="v">{pct(position.heat_pct, 2)}</div>
        <div className="k">Heat %</div>
      </div>
    </div>
  );
}

export function TickerDetail({ doc, symbol }: TickerDetailProps) {
  const [pins, setPins] = usePrefs<string[]>("pins", []);
  const pinned = pins.includes(symbol);
  const detail = doc.tickers[symbol];

  function togglePin(): void {
    setPins(pinned ? pins.filter((s) => s !== symbol) : [...pins, symbol]);
  }

  const signalRows: Row[] = (detail?.signals ?? []).map((s) => ({
    signal: s.signal,
    score: s.score,
    raw_value: s.raw_value,
  }));

  const fillRows: Row[] = (detail?.fills ?? []).map((f) => ({
    fill_date: f.fill_date,
    action: f.action,
    side: f.side,
    fill_price: f.fill_price,
    quantity: f.quantity,
    exit_fill_date: f.exit_fill_date,
    exit_fill_price: f.exit_fill_price,
    opinion_score_sum: f.opinion_score_sum,
  }));

  return (
    <div className="page ticker-detail">
      <header className="ticker-header mb-5 flex items-baseline gap-4 border-b pb-4">
        <a
          href="#/"
          className="back-link text-muted-foreground hover:text-foreground text-xs no-underline"
        >
          ← back
        </a>
        <h1 className="m-0 font-mono text-2xl font-semibold tracking-tight">{symbol}</h1>
        <button
          type="button"
          className="pin-toggle text-muted-foreground hover:text-foreground hover:border-foreground/30 ml-auto cursor-pointer rounded-md border bg-transparent px-3 py-1 font-mono text-xs aria-pressed:border-amber-500/50 aria-pressed:bg-amber-500/10 aria-pressed:text-amber-700 dark:aria-pressed:text-amber-400"
          aria-pressed={pinned}
          onClick={togglePin}
        >
          {pinned ? "★ pinned" : "☆ pin"}
        </button>
      </header>

      {!detail ? (
        <p className="empty">
          no detail exported for {symbol} — it was not in tonight's scorecard, holdings, or journal.
        </p>
      ) : (
        <>
          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5 shadow-sm">
            <h2 className="m-0 mb-3 text-base font-semibold">Score history</h2>
            <ScoreHistoryChart points={detail.score_history} />
          </section>

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5 shadow-sm">
            <h2 className="m-0 mb-3 text-base font-semibold">Signal breakdown</h2>
            {signalRows.length > 0 ? (
              <DataTable columns={SIGNAL_COLUMNS} rows={signalRows} storageKey={`ticker:${symbol}:signals`} />
            ) : (
              <p className="empty">no signals scored tonight</p>
            )}
          </section>

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5 shadow-sm">
            <h2 className="m-0 mb-3 text-base font-semibold">Research verdicts</h2>
            {detail.verdicts.length > 0 ? (
              <ul className="verdict-list">
                {detail.verdicts.map((v, i) => (
                  <li key={i}>
                    {dateShort(v.date)} — {v.verdict ?? "—"}
                    {v.thesis_path && (
                      <>
                        {" "}
                        <a href={`${REPO_URL}/blob/main/${v.thesis_path}`} target="_blank" rel="noreferrer">
                          thesis
                        </a>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">no research verdicts yet</p>
            )}
          </section>

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5 shadow-sm">
            <h2 className="m-0 mb-3 text-base font-semibold">Journal fills</h2>
            {fillRows.length > 0 ? (
              <DataTable columns={FILL_COLUMNS} rows={fillRows} storageKey={`ticker:${symbol}:fills`} />
            ) : (
              <p className="empty">no journal fills yet</p>
            )}
          </section>

          {/* Own heading, not a tail of Journal fills — unlabeled tiles right
              under that table read as the table's footer. */}
          {detail.position && (
            <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5 shadow-sm">
              <h2 className="m-0 mb-3 text-base font-semibold">Your position</h2>
              <PositionCard position={detail.position} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
