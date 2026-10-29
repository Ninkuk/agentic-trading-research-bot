// The home route (`#/`): the front door for a first-time visitor, built
// like a portfolio piece about the desk itself rather than a summary of
// tonight's market. Beats, in order: what this is (one sentence and four
// counters); one night start to finish as a scroll story, one chapter per
// step of the run, each in plain language with last night's real output;
// the graded record; three ways in. It renders outside the sidebar shell
// with its own top bar; every other route keeps the shell.
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
import { MotionConfig } from "motion/react";
import { ArrowRight, ExternalLink } from "lucide-react";
import { CardStack } from "../components/aceternity/card-stack";
import { EncryptedText } from "../components/aceternity/encrypted-text";
import { FlipWords } from "../components/aceternity/flip-words";
import { GlowingEffect } from "../components/aceternity/glowing-effect";
import { HoverBorderGradient } from "../components/aceternity/hover-border-gradient";
import { InfiniteMovingCards } from "../components/aceternity/infinite-moving-cards";
import { Button as MovingBorderButton } from "../components/aceternity/moving-border";
import { Spotlight } from "../components/aceternity/spotlight-new";
import { Terminal } from "../components/aceternity/terminal";
import { TextGenerateEffect } from "../components/aceternity/text-generate-effect";
import {
  TextRevealCard,
  TextRevealCardDescription,
  TextRevealCardTitle,
} from "../components/aceternity/text-reveal-card";
import { Timeline, type TimelineEntry } from "../components/aceternity/timeline";
import { EquityCurve } from "../charts/EquityCurve";
import { REPO_URL } from "../constants";
import { dateShort, pct } from "../format";
import {
  bestCall,
  calibration,
  callHitRate,
  callsGraded,
  drivers,
  GRADE_HORIZON,
  lastNight,
  lastRunOf,
  lastRuns,
  nightsCalled,
  record,
  researchCounts,
  thesisOneLiner,
  unprovenSignals,
  type Calibration,
  type LastNight,
  type ResearchCounts,
} from "../home/homeFacts";
import { normalizeTicker, suggestionHref, TICKER_RE } from "../home/suggest";
import type { BestCall, DashboardDoc, LastRun } from "../types";
import { ThemeToggle } from "../ui/Masthead";
import { VerdictChip } from "../ui/VerdictChip";

const HEADLINE = "A research desk that grades its own work.";
const DASHBOARD_HREF = "#/macro";

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

/** The published thesis's opening sentence, or null while loading, when
 * the file is not published, or when it has no such line. The published
 * file is the ticker's NEWEST thesis, which may postdate the graded call
 * (SAP's best call was a July buy; its newest thesis is a pass), so the
 * line is fetched only when the ticker's thesis date is the call's date. */
function useThesisOneLiner(doc: DashboardDoc, best: BestCall | null): string | null {
  const thesis = best ? doc.tickers?.[best.symbol]?.thesis : undefined;
  const symbol = best && thesis && thesis.date === best.verdict_date ? best.symbol : null;
  const [line, setLine] = useState<string | null>(null);
  useEffect(() => {
    setLine(null);
    if (!symbol || typeof fetch !== "function") return;
    let live = true;
    fetch(`./theses/${symbol}.md`)
      .then(async (r) => (r.ok ? thesisOneLiner(await r.text()) : null))
      .then((text) => live && setLine(text))
      .catch(() => live && setLine(null));
    return () => {
      live = false;
    };
  }, [symbol]);
  return line;
}

// --- hero --------------------------------------------------------------------

function Counter({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="min-w-0">
      <div className="text-foreground text-3xl font-semibold tracking-tight tabular-nums md:text-4xl">
        {value}
      </div>
      <div className="text-muted-foreground text-sm">{label}</div>
    </div>
  );
}

function Hero({ doc }: { doc: DashboardDoc }) {
  const counts = researchCounts(doc);
  const nights = nightsCalled(doc);
  const graded = callsGraded(doc);
  const best = bestCall(doc);
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
          Running nightly{nights ? ` for ${nights} nights` : ""}
          {doc.snapshot_number !== null && ` · snapshot #${doc.snapshot_number}`}
        </span>
        <h1 className="m-0 max-w-[14ch] text-5xl leading-[1.02] font-semibold tracking-tight text-balance md:text-6xl lg:text-7xl">
          <TextGenerateEffect words={HEADLINE} duration={0.6} />
        </h1>
        <p className="text-muted-foreground m-0 max-w-[58ch] text-lg md:text-xl">
          Every night it pulls official public data, has an AI write a stock thesis and then attack it, and
          keeps a public scorecard of whether those opinions were right. A person makes every actual decision.
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
          <a
            className="border-border hover:bg-muted inline-flex h-11 items-center gap-1.5 rounded-full border px-5 text-sm font-medium no-underline"
            href="#/"
            onClick={onScrollTo("scorecard")}
          >
            See the scorecard <ArrowRight aria-hidden="true" className="size-3.5" />
          </a>
          {best && (
            <a
              className="border-border hover:bg-muted inline-flex h-11 items-center gap-1.5 rounded-full border px-5 text-sm font-medium no-underline"
              href={`#/ticker/${best.symbol}`}
            >
              Read the best call so far <ArrowRight aria-hidden="true" className="size-3.5" />
            </a>
          )}
        </div>
        {(counts || graded || nights) && (
          <div className="border-border grid max-w-3xl grid-cols-2 gap-5 border-t pt-6 sm:grid-cols-4">
            {counts && <Counter value={counts.theses} label="theses written" />}
            {counts && <Counter value={counts.passes} label="ended in a pass" />}
            {graded && <Counter value={graded} label="calls graded so far" />}
            {nights && <Counter value={nights} label="nights, no gaps" />}
          </div>
        )}
      </div>
    </header>
  );
}

// --- the story: one night, chapter by chapter ---------------------------------

// Seals are the agencies' own (public domain; public/logos/README.md).
// FINRA and Cboe are private trademarks and the NY Fed has no public-domain
// seal, so those three show as wordmarks.
const SOURCES = [
  { name: "The Federal Reserve", title: "Interest rates, inflation, and the Fed's own balance sheet", quote: "The numbers behind every rate headline, straight from the people who set the rate.", logo: "./logos/fed.png" },
  { name: "The US Treasury", title: "Daily yields and auction results", quote: "What the government pays to borrow, and how eager buyers were at the last auction.", logo: "./logos/treasury.png" },
  { name: "The SEC", title: "Company filings", quote: "Earnings, insider trades, restated numbers, and anyone crossing 5% of a company.", logo: "./logos/sec.png" },
  { name: "The CFTC", title: "Weekly futures positions", quote: "What professional traders are actually betting on, by contract, every week.", logo: "./logos/cftc.png" },
  { name: "FINRA", title: "Short selling and off-exchange volume", quote: "How much of today's trading was betting against a stock, and how much happened in the dark." },
  { name: "Cboe", title: "The fear index and the options mood", quote: "How nervous the options market is, and whether it expects that to get worse." },
  { name: "The New York Fed", title: "Overnight funding markets", quote: "The plumbing that shows stress before prices do." },
  { name: "The EIA", title: "Weekly energy inventories", quote: "Crude, fuel and gas stocks, with the change from last week.", logo: "./logos/eia.png" },
  { name: "The USDA", title: "Monthly grain supply", quote: "World supply and demand for the major crops.", logo: "./logos/usda.png" },
];

/** The night's jobs as the terminal replays them: the wrapper's real
 * `main.py` invocation, then the summary line the run printed and its
 * wall time. Jobs whose output matched nothing show the command alone. */
function terminalScript(runs: LastRun[]): { commands: string[]; outputs: Record<number, string[]> } {
  const commands: string[] = [];
  const outputs: Record<number, string[]> = {};
  runs.forEach((r, i) => {
    commands.push(`uv run python main.py ${r.command}`);
    outputs[i] = [
      ...(r.summary ? [r.summary] : []),
      `[${r.at}] done in ${r.seconds}s, exit ${r.exit}`,
    ];
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

function Facts({ items }: { items: string[] }) {
  return (
    <ul className="text-foreground m-0 grid max-w-[60ch] list-none gap-2 p-0">
      {items.map((t) => (
        <li key={t} className="flex gap-3">
          <span aria-hidden="true" className="bg-primary mt-2.5 size-1.5 shrink-0 rounded-full" />
          <span>{t}</span>
        </li>
      ))}
    </ul>
  );
}

const READ_JOBS = new Set(["treasury", "fred", "cboe-stats", "short-volume", "short-interest", "edgar"]);

function ReadChapter({ doc, night }: { doc: DashboardDoc; night: LastNight }) {
  const runs = lastRuns(doc).filter((r) => READ_JOBS.has(r.job));
  const d = drivers(doc);
  return (
    <div className="grid gap-6">
      <Prose>
        About twenty official sources, the places the numbers actually come from. No vendor feeds, no
        scraping forums for tips. Each one is read on its own schedule by a small program that does nothing
        else, and every figure is filed with the date it was published.
      </Prose>
      {runs.length > 0 ? (
        <Terminal
          username="launchd"
          commands={terminalScript(runs).commands}
          outputs={terminalScript(runs).outputs}
          typingSpeed={28}
          delayBetweenCommands={500}
          className="max-w-2xl"
        />
      ) : (
        night.jobsRan !== null && <Chip>{night.jobsRan} jobs ran</Chip>
      )}
      {d.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {d.map((x) => (
            <Chip key={x.label}>
              {x.label}: {x.value}
              {x.band ? ` (${x.band})` : ""}
            </Chip>
          ))}
        </div>
      )}
      <InfiniteMovingCards items={SOURCES} speed="slow" className="-mx-5 w-[calc(100%+2.5rem)] sm:-mx-8 sm:w-[calc(100%+4rem)]" />
    </div>
  );
}

function RunChip({ run }: { run: LastRun | null }) {
  if (!run?.summary) return null;
  return (
    <Chip>
      [{run.at}] {run.summary}
    </Chip>
  );
}

function WriteChapter({ doc, night }: { doc: DashboardDoc; night: LastNight }) {
  return (
    // overflow-hidden: Flip Words' exiting word is absolutely positioned
    // and scaled 2x, which at phone width pokes past the viewport and
    // zooms the whole page out (see DESIGN_MEMORY's phone rule).
    <div className="relative grid gap-6 overflow-hidden">
      <Prose>
        Two things get written. A one-line read on the market's mood, decided by three fear-and-credit
        gauges with nine more watched but not voting. And a scorecard of every stock whose numbers look
        unusual tonight: heavy
        <FlipWords words={["short selling", "delivery failures", "crowd attention", "options bets"]} className="font-medium" />
        and the like. A statistically odd stock is not a good business, so the scorecard is a reading list,
        never a recommendation.
      </Prose>
      <div className="grid gap-3 sm:grid-cols-3">
        <OutputCard label="The mood" value={night.regime ?? "not called"} note="three gauges vote; nine are watched" />
        <OutputCard
          label="The scorecard"
          value={night.tickersScored !== null ? `${night.tickersScored.toLocaleString()} stocks` : "not scored"}
          note="checked for unusual numbers"
        />
        <OutputCard
          label="The reading list"
          value={night.candidates !== null ? `${night.candidates} companies` : "empty"}
          note="good businesses currently marked down"
        />
      </div>
      <RunChip run={lastRunOf(doc, "composite")} />
    </div>
  );
}

function OutputCard({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="bg-card border-border relative grid min-w-0 gap-0.5 rounded-2xl border p-4">
      <GlowingEffect disabled={false} proximity={48} spread={32} inactiveZone={0.2} borderWidth={2} />
      <span className="text-muted-foreground text-xs font-semibold tracking-widest uppercase">{label}</span>
      <span className="text-lg font-semibold tracking-tight">{value}</span>
      <span className="text-muted-foreground text-sm">{note}</span>
    </div>
  );
}

function GradeChapter({
  doc,
  cal,
  graded,
  unproven,
}: {
  doc: DashboardDoc;
  cal: Calibration | null;
  graded: number | null;
  unproven: { unproven: number; total: number } | null;
}) {
  const said = cal ? /said (\d+%), won (\d+%)/.exec(cal.verdict.text) : null;
  return (
    <div className="grid gap-6">
      <Prose>
        Weeks later, every opinion gets a report card. Each call is re-checked against simply holding the
        S&amp;P 500, the stated odds are held to account, and a market signal with too little evidence stays
        unproven rather than being trusted. Nothing adjusts itself; a person reads the grades.
      </Prose>
      <Facts
        items={[
          `Each call is re-checked 5, 10 and ${GRADE_HORIZON} trading days on.`,
          "A pass is graded too: saying no has a cost when the stock goes on to win.",
          unproven
            ? `${unproven.unproven} of ${unproven.total} market signals are still unproven.`
            : "A market signal stays unproven until it has enough independent episodes.",
        ]}
      />
      {cal && said ? (
        <TextRevealCard
          text={`It said it would win ${said[1]} of the time.`}
          revealText={`It won ${said[2]}.`}
          className="max-w-2xl"
        >
          <TextRevealCardTitle>Confidence, held to account</TextRevealCardTitle>
          <TextRevealCardDescription>
            Drag across to reveal. {graded ? `${graded} calls graded so far.` : ""}
            {cal.forecastError
              ? ` Forecast error ${cal.forecastError}${cal.baseRate ? `; guessing the base rate scores ${cal.baseRate}` : ""}.`
              : ""}
          </TextRevealCardDescription>
        </TextRevealCard>
      ) : (
        <Chip>{graded ? `${graded} calls graded` : "nothing graded yet"}</Chip>
      )}
      <RunChip run={lastRunOf(doc, "scorer")} />
    </div>
  );
}

function ResearchChapter({ doc, best, night }: { doc: DashboardDoc; best: BestCall | null; night: LastNight }) {
  const line = useThesisOneLiner(doc, best);
  return (
    <div className="grid gap-6">
      <Prose>
        One company gets the full treatment: what the business actually does and whether it has an edge,
        what today's price already assumes about its growth, and a yes or a no with stated odds of beating
        the market over the next quarter. Every number cites the filing it came from.
      </Prose>
      {best && (
        <div className="bg-card border-border grid max-w-2xl gap-3 rounded-2xl border p-5 sm:p-6">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="text-muted-foreground font-mono text-xs">research/{best.symbol}-{best.verdict_date}.md</span>
            <Chip tone="up">best call so far</Chip>
          </div>
          {line ? (
            <p className="m-0 text-lg leading-relaxed font-medium">
              <EncryptedText text={line} revealDelayMs={18} flipDelayMs={40} encryptedClassName="text-muted-foreground/60" />
            </p>
          ) : (
            <p className="text-foreground m-0 text-lg font-medium">
              <span className="sym">{best.symbol}</span>: buy, {bestCallLine(best)}.
            </p>
          )}
          <HoverBorderGradient as="a" href={`#/ticker/${best.symbol}`} containerClassName="no-underline" className="text-sm font-medium">
            Read the whole thesis
          </HoverBorderGradient>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <RunChip run={lastRunOf(doc, "research-nightly")} />
        {night.thesis && (
          <Chip>
            last night: {night.thesis.ticker} · {night.thesis.call}
          </Chip>
        )}
      </div>
    </div>
  );
}

function AttackChapter({ counts, night }: { counts: ResearchCounts | null; night: LastNight }) {
  const cards = [
    { id: 0, name: "Sound", designation: "the argument held up under attack", content: <Big n={counts?.sound} /> },
    { id: 1, name: "Flawed", designation: "the attack found a load-bearing hole", content: <Big n={counts?.flawed} /> },
    { id: 2, name: "Unproven", designation: "it rests on something that could not be checked", content: <Big n={counts?.unproven} /> },
  ];
  return (
    <div className="grid gap-6">
      <Prose>
        Then it tries to break its own argument. A second pass argues the other side, asks what would have
        to be true, and checks each of those against the evidence. The verdict is sound, flawed, or unproven,
        and flawed is common. Both passes state their odds, and the scorecard grades both.
      </Prose>
      <div className="flex justify-start py-6 pl-2">
        <CardStack items={cards} />
      </div>
      {night.thesis?.verdict && <Chip>last night: kill-thesis {night.thesis.verdict}</Chip>}
    </div>
  );
}

function Big({ n }: { n: number | undefined }) {
  return (
    <span className="text-4xl font-semibold tracking-tight tabular-nums">
      {n === undefined ? "—" : n}
      <span className="text-muted-foreground ml-2 text-base font-normal">theses</span>
    </span>
  );
}

function DecideChapter({ counts }: { counts: ResearchCounts | null }) {
  return (
    <div className="grid gap-6">
      <Prose>
        Nothing trades on its own. The notes are read in the morning, by a person. Any purchase is queued by
        hand, in small amounts, and every fill and every pass is journaled and graded like everything else.
      </Prose>
      {counts && (
        <Facts
          items={[
            `${counts.passes} of ${counts.theses} researched names ended in a pass. A high bar is the point.`,
            "Nothing here is investment advice.",
          ]}
        />
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
  const entries: TimelineEntry[] = [
    { when: "4:30pm", title: "Read", content: <ReadChapter doc={doc} night={night} /> },
    { when: "9:05pm", title: "Write an opinion", content: <WriteChapter doc={doc} night={night} /> },
    {
      when: "9:10pm",
      title: "Grade the old ones",
      content: (
        <GradeChapter doc={doc} cal={calibration(doc)} graded={callsGraded(doc)} unproven={unprovenSignals(doc)} />
      ),
    },
    { when: "10:00pm", title: "Research a name", content: <ResearchChapter doc={doc} best={bestCall(doc)} night={night} /> },
    { when: "10:00pm", title: "Attack the thesis", content: <AttackChapter counts={counts} night={night} /> },
    { when: "morning", title: "A person decides", content: <DecideChapter counts={counts} />, accent: true },
  ];
  return (
    <section id="story" className="border-border border-t py-16 md:py-24">
      <div className="page-wide">
        <div className="grid max-w-[60ch] gap-2">
          <span className="text-tone-up text-xs font-semibold tracking-widest uppercase">One night, start to finish</span>
          <h2 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">What happens while nobody is watching.</h2>
          <p className="text-muted-foreground m-0 text-base">
            Six steps, every evening, Phoenix time. The outputs below are from {doc.edition_date}.
          </p>
        </div>
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
        <div className="mb-8 grid max-w-[60ch] gap-2">
          <span className="text-tone-up text-xs font-semibold tracking-widest uppercase">The scorecard</span>
          <h2 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">Has it been right?</h2>
          <p className="text-muted-foreground m-0 text-base">
            Opinions are graded weeks later against what actually happened. Nothing re-tunes itself.
            Performance is $100 rebased; no positions, no dollar amounts.
          </p>
        </div>
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
                evidence="Not enough independent episodes yet to keep or retire them."
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
        <div className="mb-8 grid gap-2">
          <span className="text-tone-up text-xs font-semibold tracking-widest uppercase">Where next</span>
          <h2 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">Three ways in.</h2>
        </div>
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
        <div className="grid max-w-[60ch] gap-2">
          <span className="text-tone-up text-xs font-semibold tracking-widest uppercase">Suggest a name</span>
          <h2 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">Point the desk at a stock.</h2>
          <p className="text-muted-foreground m-0 text-base">
            Any US-listed name. It joins the reading list, gets the same thesis and the same attack as every
            other name, and the scorecard grades the call whether it says buy or pass.
          </p>
        </div>
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
            Opens a prefilled GitHub issue in a new tab; a GitHub account is needed. Nothing is stored here.
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
        <nav className="border-border bg-background/80 sticky top-0 z-50 border-b backdrop-blur" aria-label="primary">
          <div className="page-wide flex h-14 items-center justify-between gap-4">
            <a className="flex items-center gap-2.5 font-semibold no-underline" href="#/">
              <span aria-hidden="true" className="bg-primary size-4 rounded-full shadow-[0_0_0_4px_var(--tone-up-bg)]" />
              Agentic Trading Research Bot
            </a>
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <a
                className="border-border hover:bg-muted hidden items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium no-underline sm:inline-flex"
                href={DASHBOARD_HREF}
              >
                Tonight's report <ArrowRight aria-hidden="true" className="size-3.5" />
              </a>
            </div>
          </div>
        </nav>

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
