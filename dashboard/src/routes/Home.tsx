// The home route (`#/`): the front door for a first-time visitor, built
// like a portfolio piece about the desk itself rather than a summary of
// tonight's market. Beats, in order: what this is (one sentence and four
// counters); one night start to finish as a scroll story, one chapter per
// step of the run, each in plain language with last night's real output;
// the graded record; three ways in. It renders outside the sidebar shell
// with no bar of its own; every other route keeps the shell.
//
// Every number comes from sections the exporter already ships (homeFacts);
// a missing section drops its line rather than showing a zero. Performance
// is the $100-rebased curve only — positions, dollar amounts, heat and
// disagreements never appear here. The featured thesis is the best matured
// buy call so far (the exporter's `best_call`), not the newest: a visitor
// should land on the desk's strongest graded work, with the hit rate beside
// it so the one call never stands in for the record. Its opening sentence
// is fetched from the published thesis file and shown only when it loads.
//
// Motion is Aceternity UI's (components/aceternity): Spotlight behind the
// hero, Text Generate on the headline, Moving Border on the primary button,
// Timeline for the story, Terminal and Infinite Moving Cards for the
// sources, Flip Words for the scorecard, Text Reveal Card for calibration,
// Encrypted Text for the thesis line, Card Stack for the attack verdicts,
// Hover Border Gradient and Glowing Effect on the closing cards.
// `MotionConfig reducedMotion="user"` turns all of it into plain rendering
// for readers who asked for less motion.

import { useEffect, useState } from "react";
import { motion, MotionConfig } from "motion/react";
import { ArrowRight, Check, ClipboardCheck, Compass, ExternalLink, MessageSquarePlus, MoonStar, X, type LucideIcon } from "lucide-react";
import { Compare } from "../components/aceternity/compare";
import { GlowingEffect } from "../components/aceternity/glowing-effect";
import { DecisionSort } from "../home/DecisionSort";
import { HoverBorderGradient } from "../components/aceternity/hover-border-gradient";
import { InfiniteMovingCards } from "../components/aceternity/infinite-moving-cards";
import { Button as MovingBorderButton } from "../components/aceternity/moving-border";
import { Spotlight } from "../components/aceternity/spotlight-new";
import { Terminal } from "../components/aceternity/terminal";
import { TextGenerateEffect } from "../components/aceternity/text-generate-effect";
import { TypewriterEffect } from "../components/aceternity/typewriter-effect";
import { Timeline, type TimelineEntry } from "../components/aceternity/timeline";
import { EquityCurve } from "../charts/EquityCurve";
import { REPO_URL } from "../constants";
import { dateShort, pct } from "../format";
import {
  bestCall,
  calibration,
  callHitRate,
  callsGraded,
  decisionDeck,
  GRADE_HORIZON,
  lastNight,
  lastRuns,
  nightsCalled,
  plainSummary,
  record,
  researchCounts,
  scoredSymbols,
  stocksBought,
  thesisCallout,
  thesisHeadings,
  thesisKillVerdict,
  thesisOneLiner,
  unprovenSignals,
  type Calibration,
  type DeckCard,
  type HitRate,
  type LastNight,
  type ResearchCounts,
} from "../home/homeFacts";
import { normalizeTicker, suggestionHref, TICKER_RE } from "../home/suggest";
import { StatTicker, type Stat } from "../home/StatTicker";
import type { BestCall, DashboardDoc, LastRun } from "../types";
import { VerdictChip } from "../ui/VerdictChip";

const HEADLINE = "A research desk that grades its own work.";


/** In-page navigation that leaves the hash alone: a bare `#story` would be
 * parsed as a section route and send the reader to a strand page. */
function scrollToId(id: string): void {
  document.getElementById(id)?.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

function onScrollTo(id: string) {
  return (e: React.MouseEvent) => {
    e.preventDefault();
    scrollToId(id);
  };
}

/** UTC export timestamp → the reader's local clock. */
function formatGeneratedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** "+14.8 points vs SPY over 21 trading days, called Sep 26". Excess is a
 * fraction of return; points are the plain-English unit the curve's chip
 * already uses. */
function bestCallLine(b: BestCall): string {
  const pts = (b.excess * 100).toFixed(1);
  return `${b.excess >= 0 ? "+" : ""}${pts} points vs SPY over ${b.horizon} trading days, called ${dateShort(b.verdict_date)}`;
}

interface ThesisPeek {
  title: string | null;
  line: string | null;
  headings: string[];
  /** The attack pass's strongest objection, and its label on the thesis. */
  attack: string | null;
  killVerdict: string | null;
}

/** A published thesis, peeked: its title line, its opening sentence and
 * its section headings. Null while loading, when the file is not
 * published, or when it has none of those. `file` is the published path
 * under theses/: `<SYM>.md` is a ticker's newest thesis, `<SYM>-<date>.md`
 * the exact write-up behind a graded call. */
function useThesisPeek(file: string | null): ThesisPeek | null {
  const [peek, setPeek] = useState<ThesisPeek | null>(null);
  useEffect(() => {
    setPeek(null);
    if (!file || typeof fetch !== "function") return;
    let live = true;
    fetch(`./theses/${file}`)
      .then(async (r) => {
        if (!r.ok) return null;
        const md = await r.text();
        const title = md.split("\n").find((l) => l.startsWith("# "))?.slice(2).trim() ?? null;
        const line = thesisOneLiner(md);
        const headings = thesisHeadings(md);
        const attack = thesisCallout(md, "Closest attack");
        const killVerdict = thesisKillVerdict(md);
        return line || headings.length > 0 ? { title, line, headings, attack, killVerdict } : null;
      })
      .then((p) => live && setPeek(p))
      .catch(() => live && setPeek(null));
    return () => {
      live = false;
    };
  }, [file]);
  return peek;
}

// --- hero --------------------------------------------------------------------

function Hero({ doc }: { doc: DashboardDoc }) {
  const counts = researchCounts(doc);
  const nights = nightsCalled(doc);
  const bought = stocksBought(doc);
  const rec = record(doc);
  const stats: Stat[] = [];
  if (counts) stats.push({ value: counts.theses, label: "stocks researched" });
  if (bought) stats.push({ value: bought, label: "stocks bought" });
  if (nights) stats.push({ value: nights, label: "nights running" });
  if (rec) stats.push({ value: rec.picks, label: rec.picks.startsWith("-") ? "down overall" : "up overall" });
  return (
    <header className="relative overflow-hidden">
      <Spotlight
        gradientFirst="radial-gradient(68.54% 68.72% at 55.02% 31.46%, rgba(0,200,5,.12) 0, rgba(0,200,5,.03) 50%, rgba(0,200,5,0) 80%)"
        gradientSecond="radial-gradient(50% 50% at 50% 50%, rgba(0,200,5,.09) 0, rgba(0,200,5,.03) 80%, transparent 100%)"
        gradientThird="radial-gradient(50% 50% at 50% 50%, rgba(0,200,5,.06) 0, rgba(0,200,5,.03) 80%, transparent 100%)"
      />
      <div aria-hidden="true" className="home-grid pointer-events-none absolute inset-0" />
      <div className="page-wide relative grid gap-7 py-20 md:py-28">
        <span className="border-border text-muted-foreground inline-flex w-max items-center gap-2 rounded-full border px-3.5 py-1 text-sm">
          <span aria-hidden="true" className="bg-primary size-2 rounded-full shadow-[0_0_0_3px_var(--tone-up-bg)]" />
          Running every night
        </span>
        <h1 className="m-0 max-w-[14ch] text-5xl leading-[1.02] font-semibold tracking-tight text-balance md:text-6xl lg:text-7xl">
          <TextGenerateEffect words={HEADLINE} duration={0.6} />
        </h1>
        <p className="text-muted-foreground m-0 max-w-[58ch] text-lg md:text-xl">
          Every evening it reads about twenty official sources, writes up a few stocks, and goes back to check
          how its earlier opinions worked out. A person makes every actual decision.
        </p>
        <div className="flex flex-wrap gap-3">
          <MovingBorderButton
            as="a"
            href="#/"
            onClick={onScrollTo("story")}
            borderRadius="999px"
            duration={3200}
            containerClassName="h-11 w-auto text-sm no-underline"
            borderClassName="bg-[radial-gradient(var(--primary)_40%,transparent_60%)]"
            className="bg-background/80 border-border text-foreground px-5 font-medium"
          >
            Watch one night
          </MovingBorderButton>
        </div>
        {stats.length > 0 && (
          <div className="border-border border-t pt-6">
            <StatTicker stats={stats} />
          </div>
        )}
      </div>
    </header>
  );
}

/** Section heading in the catalog style: an icon tile with a colored
 * label, a regular-weight headline, a muted lede. */
function SectionTitle({
  icon: Icon,
  label,
  title,
  note,
  className,
}: {
  icon: LucideIcon;
  label: string;
  title: string;
  note?: string;
  className?: string;
}) {
  return (
    <div className={`grid max-w-[60ch] gap-5 ${className ?? ""}`}>
      <div className="flex items-center gap-3">
        <span className="bg-tone-up-bg text-tone-up grid size-10 place-items-center rounded-lg">
          <Icon aria-hidden="true" className="size-5" />
        </span>
        <span className="text-tone-up text-lg font-medium">{label}</span>
      </div>
      <h2 className="m-0 text-4xl leading-[1.08] font-medium tracking-tight text-balance md:text-5xl">{title}</h2>
      {note && <p className="text-muted-foreground m-0 max-w-[52ch] text-lg leading-relaxed">{note}</p>}
    </div>
  );
}

// --- the story: one night, chapter by chapter ---------------------------------

// Seals are the agencies' own (public domain; public/logos/README.md).
// FINRA and Cboe are private trademarks and the NY Fed has no public-domain
// seal, so those three show as wordmarks.
const SOURCES = [
  { name: "The Federal Reserve", title: "Interest rates, inflation, and the Fed's own balance sheet", quote: "Economic statistics: interest rates, inflation, the money supply, and the Fed's own balance sheet.", logo: "./logos/fed.png" },
  { name: "The US Treasury", title: "Daily yields and auction results", quote: "What the government pays to borrow at each maturity, and how each auction of new debt went.", logo: "./logos/treasury.png" },
  { name: "The SEC", title: "Company filings", quote: "Company filings: quarterly reports, insider trades, restated numbers, and large new shareholders.", logo: "./logos/sec.png" },
  { name: "The CFTC", title: "Weekly futures positions", quote: "The weekly report on what professional futures traders are betting, contract by contract.", logo: "./logos/cftc.png" },
  { name: "FINRA", title: "Short selling and off-exchange volume", quote: "How much of each day's trading was short selling, and how much happened away from the public exchanges." },
  { name: "Cboe", title: "The fear index and the options mood", quote: "The fear index and the rest of the options market's mood." },
  { name: "The New York Fed", title: "Overnight funding markets", quote: "Overnight lending rates between banks, which tend to show strain early." },
  { name: "The EIA", title: "Weekly energy inventories", quote: "Weekly stocks of crude oil, fuel and natural gas.", logo: "./logos/eia.png" },
  { name: "The USDA", title: "Monthly grain supply", quote: "Monthly supply and demand estimates for the major crops.", logo: "./logos/usda.png" },
];

/** The night's jobs as the terminal replays them: the wrapper's real
 * `main.py` invocation, then what it fetched in plain words and the wall
 * time. Jobs whose output matched nothing show the command alone. */
function terminalScript(runs: LastRun[]): { commands: string[]; outputs: Record<number, string[]> } {
  const commands: string[] = [];
  const outputs: Record<number, string[]> = {};
  runs.forEach((r, i) => {
    commands.push(`uv run python main.py ${r.command}`);
    const plain = plainSummary(r);
    outputs[i] = [...(plain ? [plain] : []), `done in ${r.seconds}s`];
  });
  return { commands, outputs };
}

function Chip({ children, tone }: { children: React.ReactNode; tone?: "up" }) {
  return (
    <span
      className={
        tone === "up"
          ? "bg-tone-up-bg text-tone-up inline-flex w-fit max-w-full items-center rounded-full px-2.5 py-0.5 text-sm font-medium"
          : "bg-muted border-border text-foreground inline-flex w-fit max-w-full rounded-md border px-2 py-1 font-mono text-xs break-words"
      }
    >
      {children}
    </span>
  );
}

function Prose({ children }: { children: React.ReactNode }) {
  return <p className="text-muted-foreground m-0 max-w-[60ch] text-base md:text-lg">{children}</p>;
}

const READ_JOBS = new Set(["fred", "edgar"]);

function ReadChapter({ doc, night }: { doc: DashboardDoc; night: LastNight }) {
  const runs = lastRuns(doc).filter((r) => READ_JOBS.has(r.job));
  return (
    <div className="grid gap-6">
      <Prose>
        About twenty small programs each visit one official source and file away what they find, with the
        date it was published. This is what they printed last night.
      </Prose>
      {runs.length > 0 ? (
        <Terminal
          username="~/agentic-trading-research-bot"
          commands={terminalScript(runs).commands}
          outputs={terminalScript(runs).outputs}
          typingSpeed={28}
          delayBetweenCommands={500}
          className="max-w-3xl"
        />
      ) : (
        night.jobsRan !== null && <Chip>{night.jobsRan} jobs ran</Chip>
      )}
      <InfiniteMovingCards items={SOURCES} durationSeconds={150} className="-mx-5 w-[calc(100%+2.5rem)] sm:-mx-8 sm:w-[calc(100%+4rem)]" />
    </div>
  );
}

/** The night's opinion as the desk writes it: the scorecard's real symbols
 * as a faint wall behind a note card, the flagged ones lit in their lean's
 * tone, and the sentence typed in word by word once it scrolls into view. */
function SymbolWall({ doc }: { doc: DashboardDoc }) {
  const symbols = scoredSymbols(doc, 60);
  if (symbols.length === 0) return null;
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 flex flex-wrap content-start gap-x-3 gap-y-1.5 overflow-hidden p-4 font-mono text-[11px] leading-none tracking-wide select-none [mask-image:radial-gradient(ellipse_at_top_right,black_20%,transparent_75%)]"
    >
      {symbols.map((s) => (
        <span
          key={s.symbol}
          className={
            s.flagged && s.score > 0
              ? "text-tone-up"
              : s.flagged && s.score < 0
                ? "text-tone-down"
                : "text-muted-foreground/40"
          }
        >
          {s.symbol}
        </span>
      ))}
    </div>
  );
}

function nightStats(night: LastNight): Stat[] {
  const stats: Stat[] = [];
  if (night.regime) {
    // "Risk-on, 92nd night" → the streak as the figure, the mood in plain
    // words as its label: the inputs are fear gauges, so risk-on is calm, risk-off nervous.
    const n = /(\d+)(?:st|nd|rd|th) night/.exec(night.regime)?.[1];
    const mood = /risk-on/i.test(night.regime) ? "calm" : /risk-off/i.test(night.regime) ? "nervous" : "mixed";
    stats.push(n ? { value: Number(n), label: `${mood} nights in a row` } : { value: mood, label: "the market tonight", tick: false });
  } else {
    stats.push({ value: "none", label: "no mood call tonight", tick: false });
  }
  if (night.tickersScored !== null) stats.push({ value: night.tickersScored, label: "stocks checked" });
  if (night.candidates !== null) stats.push({ value: night.candidates, label: "worth a closer look" });
  return stats;
}

function WriteChapter({ doc, night }: { doc: DashboardDoc; night: LastNight }) {
  const stats = nightStats(night);
  return (
    <div className="grid gap-6">
      <Prose>
        A second set of programs reads what was collected and writes a one-line read on the market's mood,
        plus a list of stocks whose numbers look unusual.
      </Prose>
      <div className="bg-card border-border relative max-w-2xl overflow-hidden rounded-2xl border p-6 sm:p-8">
        <SymbolWall doc={doc} />
        <div className="text-muted-foreground relative mb-4 font-mono text-xs">tonight's note</div>
        <StatTicker stats={stats} className="relative" />
      </div>
    </div>
  );
}

interface ReportRow {
  label: string;
  result: string;
  mark: "pass" | "fail";
  /** Wins and losses behind the mark, for the split bar; absent for the odds row. */
  wins?: number;
  losses?: number;
}

/** The grader's own report card, from the real grades: each row lands
 * with a short stagger as it scrolls into view, then the stamp drops.
 * Wins and losses both show, as counts and as a two-tone bar. */
function reportRows(cal: Calibration | null, buy: HitRate | null, pass: HitRate | null): ReportRow[] {
  const rows: ReportRow[] = [];
  const split = (label: string, h: HitRate) => {
    const wins = Math.round(h.rate * h.n);
    rows.push({ label, result: `${wins} right, ${h.n - wins} wrong`, mark: h.rate >= 0.5 ? "pass" : "fail", wins, losses: h.n - wins });
  };
  if (buy) split("Buy calls", buy);
  if (pass) split("Pass calls", pass);
  const said = cal ? /said (\d+)%, won (\d+)%/.exec(cal.verdict.text) : null;
  if (said) {
    const gap = Math.abs(Number(said[1]) - Number(said[2]));
    rows.push({ label: "Its own odds", result: `said ${said[1]}%, won ${said[2]}%`, mark: gap <= 5 ? "pass" : "fail" });
  }
  return rows;
}

const MARK = {
  pass: { Icon: Check, className: "text-tone-up border-tone-up/40 bg-tone-up-bg" },
  fail: { Icon: X, className: "text-tone-down border-tone-down/40 bg-tone-down-bg" },
};

function ReportCard({ rows, graded }: { rows: ReportRow[]; graded: number | null }) {
  return (
    <motion.div
      className="bg-card border-border relative max-w-2xl overflow-hidden rounded-2xl border p-6 sm:p-8"
      initial="rest"
      whileInView="in"
      viewport={{ once: true, amount: 0.5 }}
    >
      <div className="text-muted-foreground mb-4 font-mono text-xs">
        report card{graded !== null && ` · ${graded} calls graded`}
      </div>
      <ul className="m-0 grid list-none gap-0 p-0">
        {rows.map((r, i) => (
          <motion.li
            key={r.label}
            className="border-border flex items-center gap-4 border-t py-3 first:border-t-0"
            variants={{ rest: { opacity: 0, x: -8 }, in: { opacity: 1, x: 0, transition: { delay: 0.15 + i * 0.25, duration: 0.35 } } }}
          >
            <span className={`grid size-7 shrink-0 place-items-center rounded-full border ${MARK[r.mark].className}`}>
              {(() => {
                const Icon = MARK[r.mark].Icon;
                return <Icon aria-hidden="true" className="size-4" strokeWidth={2.5} />;
              })()}
            </span>
            <span className="font-medium">{r.label}</span>
            <span className="ml-auto grid justify-items-end gap-1">
              <span className="text-muted-foreground text-right text-sm tabular-nums">{r.result}</span>
              {r.wins !== undefined && r.losses !== undefined && r.wins + r.losses > 0 && (
                <span aria-hidden="true" className="flex h-1.5 w-28 overflow-hidden rounded-full">
                  <span className="bg-tone-up" style={{ width: `${(100 * r.wins) / (r.wins + r.losses)}%` }} />
                  <span className="bg-tone-down flex-1" />
                </span>
              )}
            </span>
          </motion.li>
        ))}
      </ul>
      <motion.span
        aria-hidden="true"
        className="text-tone-hold border-tone-hold pointer-events-none absolute top-5 right-6 rotate-[8deg] rounded-md border-2 px-2.5 py-0.5 font-mono text-sm font-semibold tracking-widest uppercase sm:top-6 sm:right-8"
        variants={{ rest: { opacity: 0, scale: 1.8 }, in: { opacity: 0.9, scale: 1, transition: { delay: 0.3 + rows.length * 0.25, type: "spring", stiffness: 500, damping: 22 } } }}
      >
        graded
      </motion.span>
    </motion.div>
  );
}

function GradeChapter({
  cal,
  buy,
  pass,
  graded,
}: {
  cal: Calibration | null;
  buy: HitRate | null;
  pass: HitRate | null;
  graded: number | null;
}) {
  const rows = reportRows(cal, buy, pass);
  return (
    <div className="grid gap-6">
      <Prose>
        A grader goes back and checks how each past opinion turned out against simply holding an S&amp;P 500
        fund, and whether the odds the research gave itself held up. Nothing tunes itself automatically.
      </Prose>
      {rows.length > 0 ? <ReportCard rows={rows} graded={graded} /> : <Chip>nothing graded yet</Chip>}
    </div>
  );
}

interface Featured {
  ticker: string;
  date: string;
  file: string;
  call: string;
  verdict: string | null;
}

/** The write-up the story follows: the best graded call's own (a
 * well-known name, and the thesis that actually earned the grade), else
 * last night's. */
function featuredThesis(best: BestCall | null, night: LastNight): Featured | null {
  if (best) return { ticker: best.symbol, date: best.verdict_date, file: `${best.symbol}-${best.verdict_date}.md`, call: "buy", verdict: null };
  if (night.thesis) {
    const t = night.thesis;
    return { ticker: t.ticker, date: t.date, file: `${t.ticker}.md`, call: t.call, verdict: t.verdict };
  }
  return null;
}

function ResearchChapter({ featured, peek }: { featured: Featured | null; peek: ThesisPeek | null }) {
  return (
    <div className="grid gap-6">
      <Prose>
        An AI assistant researches one stock from the reading list: what the company does, what growth the
        price already assumes, and a buy or a pass with stated odds. Every number points to the filing it
        came from.
      </Prose>
      {featured && (
        // The write-up as the markdown file it is: the title line, the
        // opening sentence typed out, then the section headings landing one
        // by one, all in mono with the markdown marks showing.
        <div className="bg-card border-border relative max-w-2xl overflow-hidden rounded-2xl border font-mono text-[13px] leading-relaxed sm:text-sm">
          <div className="border-border text-muted-foreground flex items-center gap-3 border-b px-5 py-3 text-xs sm:px-6">
            <span className="flex gap-1.5" aria-hidden="true">
              <span className="bg-border size-2.5 rounded-full" />
              <span className="bg-border size-2.5 rounded-full" />
              <span className="bg-border size-2.5 rounded-full" />
            </span>
            <span className="truncate">research/{featured.ticker}-{featured.date}.md</span>
          </div>
          <div className="grid gap-4 p-5 sm:p-6">
            <p className="m-0 font-semibold">
              <span className="text-tone-up">#</span> {peek?.title ?? `${featured.ticker} — ${featured.date}`}
            </p>
            {peek?.line && (
              <p className="border-border m-0 border-l-2 pl-4">
                <span className="text-tone-up">&gt;</span> <span className="font-semibold">**In one sentence:**</span>{" "}
                <TypewriterEffect
                  words={peek.line.split(" ").map((text) => ({ text }))}
                  className="inline"
                  cursorClassName="ml-0.5"
                />
              </p>
            )}
            {peek && peek.headings.length > 0 && (
              <ol className="text-muted-foreground m-0 grid list-none gap-1 p-0">
                {peek.headings.map((h, i) => (
                  <motion.li
                    key={h}
                    className="truncate"
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + (peek.line?.length ?? 0) * 0.1 + i * 0.18, duration: 0.3 }}
                  >
                    <span className="text-tone-up">##</span> {h}
                  </motion.li>
                ))}
              </ol>
            )}
          </div>
          <div className="border-border flex flex-wrap items-center justify-between gap-3 border-t px-5 py-3 font-sans sm:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={featured.call === "buy" ? "up" : undefined}>{featured.call}</Chip>
              {featured.verdict && <Chip>kill-thesis: {featured.verdict}</Chip>}
            </div>
            <HoverBorderGradient
              as="a"
              href={`#/ticker/${featured.ticker}`}
              containerClassName="no-underline"
              className="text-sm font-medium"
            >
              Read the whole thesis
            </HoverBorderGradient>
          </div>
        </div>
      )}
    </div>
  );
}

/** The divider's one pass: across to the attack, then back to rest in
 * the middle with half of each side showing. */
const ATTACK_PATH = [0, 50];

const VERDICT_TONE: Record<string, string> = {
  sound: "text-tone-up border-tone-up",
  flawed: "text-tone-down border-tone-down",
  unproven: "text-tone-hold border-tone-hold",
};

/** One face of the comparison: a tinted sheet with the side's label and
 * its sentence. Both faces sit in the same grid cell, so each stretches to
 * the taller one. */
function Side({ tone, label, text }: { tone: "up" | "down"; label: string; text: string }) {
  // The tone backgrounds are translucent; the card base keeps the other
  // face from showing through as the divider wipes.
  const tint = tone === "up" ? "bg-tone-up-bg" : "bg-tone-down-bg";
  const ink = tone === "up" ? "text-tone-up" : "text-tone-down";
  return (
    <div className="bg-card relative h-full">
      <div className={`absolute inset-0 ${tint}`} />
      <div className="relative px-5 py-5 sm:px-6">
        <div className={`mb-2 font-mono text-[11px] tracking-wide uppercase ${ink}`}>{label}</div>
        <p className="text-foreground m-0 text-sm leading-relaxed sm:text-base">{text}</p>
      </div>
    </div>
  );
}

function AttackChapter({
  featured,
  peek,
  counts,
}: {
  featured: Featured | null;
  peek: ThesisPeek | null;
  counts: ResearchCounts | null;
}) {
  const verdict = peek?.killVerdict ?? featured?.verdict ?? null;
  const total = counts ? counts.sound + counts.flawed + counts.unproven : 0;
  return (
    <div className="grid gap-6">
      <Prose>
        The same assistant is then asked to argue the other side: what would have to be true for the thesis
        to hold, and where the evidence is thin. It labels the write-up sound, flawed, or unproven, and
        flawed is not rare.
      </Prose>
      {featured && peek?.line && (
        // The exchange, from the real write-up: the thesis's own sentence,
        // then the attack's strongest objection, then the label it got.
        <div className="bg-card border-border relative max-w-2xl overflow-hidden rounded-2xl border">
          <div className="border-border text-muted-foreground flex items-center justify-between gap-3 border-b px-5 py-3 font-mono text-xs sm:px-6">
            <span>{featured.ticker} · the thesis vs. the attack</span>
          </div>
          <div className="grid gap-4 p-5 sm:p-6">
            <Compare
              className="border-border rounded-2xl border"
              first={<Side tone="up" label="the thesis" text={peek.line} />}
              second={
                <Side
                  tone="down"
                  label="the attack"
                  text={peek.attack ?? "No written objection survived; the attack found nothing load-bearing."}
                />
              }
              initialSliderPercentage={100}
              autoplay
              autoplayPath={ATTACK_PATH}
              autoplayDuration={5000}
            />
            {verdict && (
              <motion.div
                className="flex items-center justify-center gap-3 pt-1"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true, amount: 0.6 }}
                transition={{ delay: 1.1 }}
              >
                <span className="text-muted-foreground text-sm">verdict</span>
                <motion.span
                  className={`rounded-md border-2 px-2.5 py-0.5 font-mono text-sm font-semibold tracking-widest uppercase ${VERDICT_TONE[verdict] ?? "text-muted-foreground border-border"}`}
                  initial={{ scale: 1.8, rotate: -6 }}
                  whileInView={{ scale: 1, rotate: -4 }}
                  viewport={{ once: true, amount: 0.6 }}
                  transition={{ delay: 1.1, type: "spring", stiffness: 500, damping: 22 }}
                >
                  {verdict}
                </motion.span>
              </motion.div>
            )}
          </div>
        </div>
      )}
      {counts && total > 0 && (
        <div className="grid max-w-2xl gap-2">
          <div aria-label="attack verdicts so far" className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full">
            <span className="bg-tone-up" style={{ width: `${(100 * counts.sound) / total}%` }} />
            <span className="bg-tone-down" style={{ width: `${(100 * counts.flawed) / total}%` }} />
            <span className="bg-tone-hold flex-1" />
          </div>
          <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span>
              <span className="text-tone-up font-medium">{counts.sound}</span> sound
            </span>
            <span>
              <span className="text-tone-down font-medium">{counts.flawed}</span> flawed
            </span>
            <span>
              <span className="text-tone-hold font-medium">{counts.unproven}</span> unproven
            </span>
            <span className="ml-auto">of {total} write-ups attacked</span>
          </div>
        </div>
      )}
    </div>
  );
}

function DecideChapter({ counts, deck }: { counts: ResearchCounts | null; deck: DeckCard[] }) {
  return (
    <div className="grid gap-6">
      <Prose>
        In the morning a person reads the notes. Nothing here trades on its own; a purchase is queued by
        hand, in a small amount, and graded like everything else.
      </Prose>
      {counts && deck.length > 0 && (
        // The newest write-ups dealt onto two piles; the totals are every
        // call so far, so the buy pile stays short.
        <DecisionSort deck={deck} totals={counts} className="max-w-2xl" />
      )}
      <HoverBorderGradient
        as="a"
        href="#/"
        onClick={onScrollTo("scorecard")}
        containerClassName="no-underline"
        className="text-sm font-medium"
      >
        See the scorecard
      </HoverBorderGradient>
    </div>
  );
}

function Story({ doc }: { doc: DashboardDoc }) {
  const night = lastNight(doc);
  const counts = researchCounts(doc);
  const deck = decisionDeck(doc);
  const featured = featuredThesis(bestCall(doc), night);
  const peek = useThesisPeek(featured?.file ?? null);
  const entries: TimelineEntry[] = [
    { when: "4:30pm", title: "Read", content: <ReadChapter doc={doc} night={night} /> },
    { when: "9:00pm", title: "Gauge the market", content: <WriteChapter doc={doc} night={night} /> },
    {
      when: "9:30pm",
      title: "Grade the old ones",
      content: (
        <GradeChapter
          cal={calibration(doc)}
          buy={callHitRate(doc, "buy")}
          pass={callHitRate(doc, "pass")}
          graded={callsGraded(doc)}
        />
      ),
    },
    { when: "10:00pm", title: "Research a name", content: <ResearchChapter featured={featured} peek={peek} /> },
    { when: "10:00pm", title: "Play devil's advocate", content: <AttackChapter featured={featured} peek={peek} counts={counts} /> },
    { when: "6:30am", title: "A person decides", content: <DecideChapter counts={counts} deck={deck} />, accent: true },
  ];
  return (
    <section id="story" className="border-border border-t py-16 md:py-24">
      <div className="page-wide">
        <SectionTitle
          icon={MoonStar}
          label="One night"
          title="What happens every evening."
          note="Six jobs on a schedule. These are last night's outputs."
        />
        <Timeline data={entries} />
      </div>
    </section>
  );
}

// --- the record ----------------------------------------------------------------

function Grade({ value, label, evidence, href }: { value: string; label: string; evidence: string; href: string }) {
  return (
    <article className="bg-card border-border relative grid min-w-0 gap-1 rounded-2xl border p-5">
      <GlowingEffect disabled={false} proximity={48} spread={32} inactiveZone={0.2} borderWidth={2} />
      <span className="text-2xl font-semibold tracking-tight tabular-nums">{value}</span>
      <span className="font-medium">{label}</span>
      <span className="text-muted-foreground text-sm">{evidence}</span>
      <a className="text-muted-foreground mt-1 text-sm underline underline-offset-4" href={href}>
        See the grading
      </a>
    </article>
  );
}

function Stat({ label, value, swatch }: { label: string; value: string; swatch: "solid" | "dashed" | "dotted" }) {
  const border = { solid: "border-chart-1", dashed: "border-muted-foreground border-dashed", dotted: "border-chart-2 border-dotted" }[swatch];
  return (
    <div className="bg-card border-border grid min-w-0 gap-0.5 rounded-2xl border px-3 py-3 sm:px-4">
      <span className="text-muted-foreground flex items-center gap-2 text-xs whitespace-nowrap sm:text-sm">
        <span aria-hidden="true" className={`inline-block w-3 shrink-0 border-t-2 sm:w-4 ${border}`} />
        {label}
      </span>
      <span className="text-xl font-semibold tracking-tight tabular-nums sm:text-2xl md:text-3xl">{value}</span>
    </div>
  );
}

function Scorecard({ doc }: { doc: DashboardDoc }) {
  const rec = record(doc);
  const buy = callHitRate(doc, "buy");
  const cal = calibration(doc);
  const sig = unprovenSignals(doc);
  const nothing = !rec && !buy && !cal && !sig;
  return (
    <section id="scorecard" className="border-border bg-muted/30 border-t py-16 md:py-24">
      <div className="page-wide">
        <SectionTitle
          icon={ClipboardCheck}
          label="The scorecard"
          title="Has it been right?"
          note="$100 put into the picks, into an S&P 500 fund, and into cash, from the first day the picks were held. No positions or dollar amounts."
          className="mb-10"
        />
        {nothing && (
          <p className="text-muted-foreground border-border rounded-2xl border border-dashed p-6 text-center">
            Nothing is graded yet. The first grades land once an opinion is {GRADE_HORIZON} trading days old.
          </p>
        )}
        {rec && (
          <>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <Stat label="The picks" value={rec.picks} swatch="solid" />
              <Stat label="SPY" value={rec.spy} swatch="dashed" />
              {rec.cash !== null && <Stat label="Cash" value={rec.cash} swatch="dotted" />}
            </div>
            <div className="border-border/70 from-card/60 rounded-3xl border bg-linear-to-b to-transparent p-1.5">
              <div className="bg-card border-border rounded-[1.1rem] border px-4 pt-4 pb-3">
                <EquityCurve rows={rec.rows} footnote={`${rec.tradingDays} trading days`} />
                <div className="text-muted-foreground mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
                  {rec.verdict && <VerdictChip verdict={rec.verdict} />}
                  <span>$100 at the {dateShort(rec.since)} close</span>
                </div>
              </div>
            </div>
          </>
        )}
        {(buy || cal || sig) && (
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {buy && (
              <Grade
                value={pct(buy.rate * 100, 0)}
                label="Buy calls right"
                evidence={`${buy.n} calls, graded ${GRADE_HORIZON} trading days later against SPY.`}
                href="#research-filter"
              />
            )}
            {cal && (
              <Grade
                value={cal.verdict.text.replace(/^[^:]*:\s*/, "")}
                label="Confidence vs results"
                evidence={
                  cal.forecastError
                    ? `Forecast error ${cal.forecastError}${cal.baseRate ? `; guessing the base rate scores ${cal.baseRate}` : ""}.`
                    : "Stated odds against actual wins."
                }
                href="#research-calibration"
              />
            )}
            {sig && (
              <Grade
                value={`${sig.unproven} of ${sig.total}`}
                label="Market signals still unproven"
                evidence="Too little history yet to keep or retire them."
                href="#signal-recommendations"
              />
            )}
          </div>
        )}
      </div>
    </section>
  );
}

// --- where next ----------------------------------------------------------------

function WhereNext({ doc }: { doc: DashboardDoc }) {
  const best = bestCall(doc);
  const counts = researchCounts(doc);
  const card = "bg-card border-border hover:bg-muted/60 grid min-w-0 gap-1 rounded-2xl border p-5 no-underline";
  return (
    <section id="next" className="border-border border-t py-16 md:py-24">
      <div className="page-wide">
        <SectionTitle icon={Compass} label="Where next" title="Where to go from here." className="mb-10" />
        <div className="grid gap-3 md:grid-cols-3">
          {best && (
            <a className={card} href={`#/ticker/${best.symbol}`}>
              <span className="flex items-center justify-between font-semibold">
                Read the best call so far <ArrowRight aria-hidden="true" className="text-muted-foreground size-4" />
              </span>
              <span className="text-muted-foreground text-sm">
                <span className="sym">{best.symbol}</span> · {bestCallLine(best)}
              </span>
            </a>
          )}
          <a className={card} href="#/research">
            <span className="flex items-center justify-between font-semibold">
              Every researched name <ArrowRight aria-hidden="true" className="text-muted-foreground size-4" />
            </span>
            <span className="text-muted-foreground text-sm">
              {counts ? `${counts.theses} theses, each with its call and how it held up under attack` : "Theses, calls, and how each held up under attack"}
            </span>
          </a>
          <a className={card} href={`${REPO_URL}#readme`} target="_blank" rel="noreferrer">
            <span className="flex items-center justify-between font-semibold">
              How it works, and the glossary <ExternalLink aria-hidden="true" className="text-muted-foreground size-4" />
            </span>
            <span className="text-muted-foreground text-sm">Plain-English pages on GitHub, with the code that produced every number.</span>
          </a>
        </div>
      </div>
    </section>
  );
}

// --- suggest a name -------------------------------------------------------------

function SuggestName() {
  const [ticker, setTicker] = useState("");
  const valid = TICKER_RE.test(ticker);
  return (
    <section id="suggest" className="border-border bg-muted/30 border-t py-16 md:py-24">
      <div className="page-wide grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:items-center">
        <SectionTitle
          icon={MessageSquarePlus}
          label="Suggest a name"
          title="Suggest a stock."
          note="Any US-listed company. It gets the same write-up, the same attack, and the same grading as everything else."
        />
        <form
          className="bg-card border-border relative grid gap-3 rounded-2xl border p-5 sm:p-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (valid) window.open(suggestionHref(ticker), "_blank", "noopener");
          }}
        >
          <GlowingEffect disabled={false} proximity={64} spread={40} inactiveZone={0.2} borderWidth={2} />
          <label className="text-muted-foreground text-sm" htmlFor="suggest-ticker">
            Ticker
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id="suggest-ticker"
              className="border-border bg-background text-foreground h-11 min-w-0 flex-1 rounded-full border px-4 font-mono text-base uppercase tracking-wide"
              value={ticker}
              onChange={(e) => setTicker(normalizeTicker(e.target.value))}
              placeholder="KTB"
              autoComplete="off"
              autoCapitalize="characters"
              inputMode="text"
              spellCheck={false}
              maxLength={8}
              aria-invalid={ticker !== "" && !valid}
            />
            <HoverBorderGradient
              as={valid ? "a" : "span"}
              href={valid ? suggestionHref(ticker) : undefined}
              target="_blank"
              rel="noreferrer"
              containerClassName={valid ? "no-underline" : "opacity-50"}
              className="text-sm font-medium"
              aria-disabled={!valid}
            >
              Suggest it
            </HoverBorderGradient>
          </div>
          <span className="text-muted-foreground text-xs">
            This opens a prefilled GitHub issue in a new tab, so a GitHub account is needed. Nothing is stored here.
          </span>
        </form>
      </div>
    </section>
  );
}

// --- page ----------------------------------------------------------------------

export function Home({ doc }: { doc: DashboardDoc }) {
  return (
    <MotionConfig reducedMotion="user">
      <div className="home bg-background text-foreground">
        <Hero doc={doc} />
        <Story doc={doc} />
        <Scorecard doc={doc} />
        <WhereNext doc={doc} />
        <SuggestName />

        <footer className="border-border text-muted-foreground border-t py-8 text-sm">
          <div className="page-wide grid gap-1.5">
            <span>
              <b className="text-foreground font-medium">Nothing here is investment advice.</b> One person's research
              tooling, published openly. All investing involves risk.
            </span>
            <span>
              Generated {formatGeneratedAt(doc.generated_at)} ·{" "}
              <a className="underline underline-offset-4" href={REPO_URL} target="_blank" rel="noreferrer">
                source on GitHub
              </a>
            </span>
          </div>
        </footer>
      </div>
    </MotionConfig>
  );
}
