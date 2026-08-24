// The per-ticker drill-down route (#/ticker/SYM): header (symbol, back
// link, pin toggle) -> screen row + research call (when on the candidates
// screen) -> score-history chart -> signal breakdown table -> research
// verdicts list -> thesis (newest, fetched from theses/<SYM>.md and rendered
// inline) -> journal fills table + position card when held.
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

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import remarkGfm from "remark-gfm";
import { REPO_URL } from "../constants";
import { dateShort, num, pct, signed, usd } from "../format";
import { useMeasuredWidth } from "../hooks/useMeasuredWidth";
import { usePrefs } from "../hooks/usePrefs";
import { tokens } from "../theme";
import type {
  Column,
  DashboardDoc,
  Row,
  ScoreHistoryPoint,
  TickerCandidate,
  TickerPosition,
  TickerThesis,
} from "../types";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../components/ui/chart";
import { DataTable } from "../ui/DataTable";
import { Masthead } from "../ui/Masthead";
import { researchVerdictPill } from "../ui/sectionCells";

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

// deep500's "does the opinion agree with the number" cell, on the page:
// the screen's numbers, how they moved while the name sat on the list, and
// the ownership call research-ticker recorded, in one block.
function ScreenBlock({ candidate }: { candidate: TickerCandidate }) {
  const trend =
    candidate.fScoreEntry !== null && candidate.fScore !== null
      ? `${num(candidate.fScoreEntry, 0)} → ${num(candidate.fScore, 0)}`
      : num(candidate.fScore, 0);
  const tenure =
    candidate.daysOnList !== null ? `on list · ${candidate.nSightings ?? 0} sightings` : "first sighting";
  return (
    <div className="tiles screen-card">
      <div className="tile">
        <div className="v">{pct(candidate.roic, 1)}</div>
        <div className="k">ROIC</div>
      </div>
      <div className="tile">
        <div className="v">{pct(candidate.fcfYield, 1)}</div>
        <div className="k">FCF yield</div>
      </div>
      <div className="tile">
        <div className="v">{trend}</div>
        <div className="k">F-score entry → now</div>
      </div>
      <div className="tile">
        <div className="v">{num(candidate.rsi, 0)}</div>
        <div className="k">RSI · {pct(candidate.high52ch, 0)} off 52w</div>
      </div>
      <div className="tile">
        <div className="v">{researchVerdictPill(candidate.verdict)}</div>
        <div className="k">
          {candidate.verdictDate ? `research call · ${dateShort(candidate.verdictDate)}` : "not yet researched"}
        </div>
      </div>
      <div className="tile">
        <div className="v">{candidate.daysOnList !== null ? `${candidate.daysOnList}d` : "new"}</div>
        <div className="k">{tenure}</div>
      </div>
    </div>
  );
}

type ThesisState = { kind: "loading" } | { kind: "ready"; md: string } | { kind: "missing" };

// Sections are the thesis template's `## ` headings; ids mirror what
// react-markdown renders (see the `h2` component below) so the jump-list
// anchors resolve.
function headingId(text: string): string {
  return `thesis-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`;
}

function ThesisBlock({ thesis }: { thesis: TickerThesis }) {
  const [state, setState] = useState<ThesisState>({ kind: "loading" });
  useEffect(() => {
    let live = true;
    setState({ kind: "loading" });
    fetch(`./${thesis.file}`)
      .then(async (r) => {
        if (!live) return;
        if (!r.ok) setState({ kind: "missing" });
        else setState({ kind: "ready", md: await r.text() });
      })
      .catch(() => live && setState({ kind: "missing" }));
    return () => {
      live = false;
    };
  }, [thesis.file]);

  const headings =
    state.kind === "ready"
      ? state.md
          .split("\n")
          .filter((l) => l.startsWith("## "))
          .map((l) => l.slice(3).trim())
      : [];

  return (
    <>
      <p className="text-muted-foreground m-0 mb-3 flex flex-wrap items-baseline gap-2 text-sm">
        <span>{dateShort(thesis.date)}</span>
        {researchVerdictPill(thesis.verdict)}
        {thesis.reopen && <span className="font-mono text-xs">reopen {thesis.reopen}</span>}
        <a href={`${REPO_URL}/blob/main/${thesis.path}`} target="_blank" rel="noreferrer">
          thesis on GitHub
        </a>
      </p>
      {state.kind === "loading" && <p className="empty">loading thesis…</p>}
      {state.kind === "missing" && (
        <p className="empty">thesis file not published yet — use the GitHub link above.</p>
      )}
      {state.kind === "ready" && (
        <>
          {headings.length > 0 && (
            <nav aria-label="thesis sections" className="thesis-nav mb-3 flex flex-wrap gap-x-3 gap-y-1 text-xs">
              {headings.map((h) => (
                <a key={h} href={`#${headingId(h)}`}>
                  {h}
                </a>
              ))}
            </nav>
          )}
          <div className="thesis-md">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ children }) => <h2 id={headingId(String(children))}>{children}</h2>,
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {state.md}
            </ReactMarkdown>
          </div>
        </>
      )}
    </>
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
      {/* Same masthead as the main page — the drill-down kept dropping the
          theme toggle and edition context, which made it feel like a
          different product. */}
      <Masthead editionDate={doc.edition_date} snapshotNumber={doc.snapshot_number} />
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
          title="Pinned tickers stay at the top of the ticker scorecard"
        >
          {pinned ? "★ pinned to top" : "☆ pin to top"}
        </button>
      </header>

      {!detail ? (
        <p className="empty">
          no detail exported for {symbol}; it was not in tonight's scorecard, holdings, or journal.
        </p>
      ) : (
        <>
          {detail.candidate && (
            <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
              <h2 className="m-0 mb-1 text-lg font-semibold">Screen</h2>
              <p className="text-muted-foreground m-0 mb-3 max-w-[75ch] text-sm">
                Tonight's candidates-screen row, how the quality read moved while the name sat on
                the list, and what deep research decided.
              </p>
              <ScreenBlock candidate={detail.candidate} />
            </section>
          )}

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
            <h2 className="m-0 mb-1 text-lg font-semibold">Score history</h2>
            <p className="text-muted-foreground m-0 mb-3 max-w-[75ch] text-sm">
              How the nightly vote on this name has moved; dots above zero lean bullish.
            </p>
            <ScoreHistoryChart points={detail.score_history} />
          </section>

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
            <h2 className="m-0 mb-1 text-lg font-semibold">Signal breakdown</h2>
            <p className="text-muted-foreground m-0 mb-3 max-w-[75ch] text-sm">
              Tonight's individual votes behind the score.
            </p>
            {signalRows.length > 0 ? (
              <DataTable columns={SIGNAL_COLUMNS} rows={signalRows} storageKey={`ticker:${symbol}:signals`} />
            ) : (
              <p className="empty">no signals scored tonight</p>
            )}
          </section>

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
            <h2 className="m-0 mb-1 text-lg font-semibold">Research verdicts</h2>
            <p className="text-muted-foreground m-0 mb-3 max-w-[75ch] text-sm">
              What deep research concluded about the business, with a link to each thesis.
            </p>
            {detail.verdicts.length > 0 ? (
              <ul className="verdict-list">
                {detail.verdicts.map((v, i) => (
                  <li key={i} className="flex items-baseline gap-2">
                    <span>{dateShort(v.date)}</span>
                    {researchVerdictPill(v.verdict)}
                    {v.thesis_path && (
                      <a href={`${REPO_URL}/blob/main/${v.thesis_path}`} target="_blank" rel="noreferrer">
                        thesis
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">no research verdicts yet</p>
            )}
          </section>

          {detail.thesis && (
            <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
              <h2 className="m-0 mb-1 text-lg font-semibold">Thesis</h2>
              <ThesisBlock thesis={detail.thesis} />
            </section>
          )}

          <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
            <h2 className="m-0 mb-1 text-lg font-semibold">Journal fills</h2>
            <p className="text-muted-foreground m-0 mb-3 max-w-[75ch] text-sm">
              Your own recorded trades in this name, matched against the opinions they answered.
            </p>
            {fillRows.length > 0 ? (
              <DataTable columns={FILL_COLUMNS} rows={fillRows} storageKey={`ticker:${symbol}:fills`} />
            ) : (
              <p className="empty">no journal fills yet</p>
            )}
          </section>

          {/* Own heading, not a tail of Journal fills — unlabeled tiles right
              under that table read as the table's footer. */}
          {detail.position && (
            <section className="ticker-block bg-card text-card-foreground mb-4 overflow-x-auto rounded-xl border p-5">
              <h2 className="m-0 mb-3 text-lg font-semibold">Your position</h2>
              <PositionCard position={detail.position} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
