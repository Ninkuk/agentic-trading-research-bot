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

import { Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { REPO_URL } from "../constants";
import { dateShort, num, pct, signed, usd } from "../format";
import { usePrefs } from "../hooks/usePrefs";
import { tokens } from "../theme";
import type { Column, DashboardDoc, Row, ScoreHistoryPoint, TickerPosition } from "../types";
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

function ScoreHistoryTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: ScoreHistoryPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="spark-tooltip">
      {dateShort(point.date)}: {signed(point.score_sum, 0)}
    </div>
  );
}

function ScoreHistoryChart({ points }: { points: ScoreHistoryPoint[] }) {
  const usable = points.filter((p) => p.score_sum !== null);
  if (usable.length < 2) {
    return <p className="empty">no score history yet</p>;
  }
  return (
    <LineChart width={560} height={180} data={usable} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
      <XAxis dataKey="date" tickFormatter={dateShort} />
      <YAxis type="number" domain={["auto", "auto"]} allowDecimals={false} />
      <Tooltip content={<ScoreHistoryTooltip />} cursor={{ stroke: tokens.edge }} />
      <ReferenceLine y={0} stroke={tokens.edge} />
      <Line
        className="score-history-line"
        type="monotone"
        dataKey="score_sum"
        stroke={tokens.hold}
        strokeWidth={2}
        dot={<ScoreDot />}
        isAnimationActive={false}
        connectNulls
      />
    </LineChart>
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
        <div className="v">{pct(position.heat_pct)}</div>
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
      <header className="ticker-header">
        <a href="#/" className="back-link">
          ← back
        </a>
        <h1>{symbol}</h1>
        <button type="button" className="pin-toggle" aria-pressed={pinned} onClick={togglePin}>
          {pinned ? "★ pinned" : "☆ pin"}
        </button>
      </header>

      {!detail ? (
        <p className="empty">
          no detail exported for {symbol} — it was not in tonight's scorecard, holdings, or journal.
        </p>
      ) : (
        <>
          <section className="ticker-block">
            <h2>Score history</h2>
            <ScoreHistoryChart points={detail.score_history} />
          </section>

          <section className="ticker-block">
            <h2>Signal breakdown</h2>
            {signalRows.length > 0 ? (
              <DataTable columns={SIGNAL_COLUMNS} rows={signalRows} storageKey={`ticker:${symbol}:signals`} />
            ) : (
              <p className="empty">no signals scored tonight</p>
            )}
          </section>

          <section className="ticker-block">
            <h2>Research verdicts</h2>
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

          <section className="ticker-block">
            <h2>Journal fills</h2>
            {fillRows.length > 0 ? (
              <DataTable columns={FILL_COLUMNS} rows={fillRows} storageKey={`ticker:${symbol}:fills`} />
            ) : (
              <p className="empty">no journal fills yet</p>
            )}
            {detail.position && <PositionCard position={detail.position} />}
          </section>
        </>
      )}
    </div>
  );
}
