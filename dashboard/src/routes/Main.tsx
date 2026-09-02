// The main page: the Summary ("Tonight in plain English" bullets + regime
// chip + an index of the strands) on `#/`, or one strand of sections on
// `#/<strand>`; the sidebar (AppShell) does the switching. Every strand is
// force-mounted and only the routed one is shown, exactly as the old tab
// strip did, so anchor links to section ids and DOM-querying tests see the
// whole document. A bare `#<section-id>` hash resolves to the strand that
// holds the section and scrolls it into view.
//
// `SECTION_COMPONENTS` maps a section id to the component that renders its
// body; a section id with no entry falls back to `GenericSection` (columns+
// rows through DataTable, tiles through StatTile, text_lines through
// TextReport) so a section the Python exporter adds before its React
// component ships never renders blank. Every registered/fallback component
// takes exactly `{sec, glossary}`.
//
// Strand grouping comes from each section's own `kicker` field (see
// strands.ts), not a hardcoded id list — a section moving strands in Python
// needs no frontend change. The seven strands render unconditionally in a
// fixed order even when a given night's document has no section for one; a
// kicker the frontend doesn't know lands in a trailing "Other" strand.
//

import { useEffect, type ComponentType, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { KpiSpark } from "../charts/KpiSpark";
import { useHashRoute, type HashRoute } from "../hooks/useHashRoute";
import { REPO_URL } from "../constants";
import { ExtLink } from "../ui/ExtLink";
import { BasisBreaks } from "../sections/BasisBreaks";
import { BookHeat } from "../sections/BookHeat";
import { BucketPerformance } from "../sections/BucketPerformance";
import { CandidateEfficacy } from "../sections/CandidateEfficacy";
import { Candidates } from "../sections/Candidates";
import { Disagreements } from "../sections/Disagreements";
import { GroupHeat } from "../sections/GroupHeat";
import { Health } from "../sections/Health";
import { HumanFilter } from "../sections/HumanFilter";
import { Pending } from "../sections/Pending";
import { PortfolioVsSpy } from "../sections/PortfolioVsSpy";
import { PositionHeat } from "../sections/PositionHeat";
import { Regime } from "../sections/Regime";
import { RegimePerformance } from "../sections/RegimePerformance";
import { RegimeTimelineSection } from "../sections/RegimeTimelineSection";
import { ResearchReopens } from "../sections/ResearchReopens";
import { Scorecard } from "../sections/Scorecard";
import { SignalEfficacy } from "../sections/SignalEfficacy";
import { SignalRecommendations } from "../sections/SignalRecommendations";
import { SizeCaps } from "../sections/SizeCaps";
import { YieldCurve } from "../sections/YieldCurve";
import { TraderScorecard } from "../sections/TraderScorecard";
import {
  STRAND_BLURBS,
  strandId,
  strandLabels,
  strandOfSection,
  strandSections,
  type StrandLabel,
} from "../strands";
import type { DashboardDoc, Glossary, Section, Tone } from "../types";
import { Card, CardContent } from "../components/ui/card";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "../components/ui/item";
import { Separator } from "../components/ui/separator";
import { DataTable } from "../ui/DataTable";
import { SectionShell } from "../ui/SectionShell";
import { makeSectionCell, visibleColumns } from "../ui/sectionCells";
import { QuietList, isQuiet } from "../ui/QuietList";
import { StrandNav } from "../ui/StrandNav";
import { StatTile } from "../ui/StatTile";
import { TextReport } from "../ui/TextReport";
import { VerdictChip } from "../ui/VerdictChip";

interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

const TONE_DOT: Record<Tone, string> = {
  on: "var(--tone-up)",
  off: "var(--tone-down)",
  mid: "var(--tone-hold)",
};

/** UTC export timestamp → the reader's local clock ("Jul 30, 2026, 10:31 AM").
 * Falls back to the raw string if the timestamp doesn't parse. */
function formatGeneratedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/** Wrap known ticker symbols in hero-bullet text with drill-down links —
 * the hero names the one thing worth attention tonight, so it must also be
 * the path to it. Only exact uppercase tokens that match an exported
 * ticker qualify, so prose words can't false-positive. */
function linkifyTickers(text: string, known: Set<string>): ReactNode[] {
  return text.split(/\b/).map((part, i) =>
    part.length >= 2 && /^[A-Z]+$/.test(part) && known.has(part) ? (
      <a key={i} className="sym" href={`#/ticker/${part}`}>
        {part}
      </a>
    ) : (
      part
    ),
  );
}

// macro-drivers has no entry: GenericSection's tiles path renders its
// value+delta tiles with their sparklines inside Macro.
const SECTION_COMPONENTS: Record<string, ComponentType<SectionComponentProps>> = {
  regime: Regime,
  "regime-timeline": RegimeTimelineSection,
  candidates: Candidates,
  "research-reopens": ResearchReopens,
  scorecard: Scorecard,
  "signal-efficacy": SignalEfficacy,
  "bucket-performance": BucketPerformance,
  "human-filter": HumanFilter,
  "regime-performance": RegimePerformance,
  pending: Pending,
  "basis-breaks": BasisBreaks,
  "book-heat": BookHeat,
  "group-heat": GroupHeat,
  "position-heat": PositionHeat,
  disagreements: Disagreements,
  "size-caps": SizeCaps,
  "signal-recommendations": SignalRecommendations,
  "trader-scorecard": TraderScorecard,
  "equity-curve": PortfolioVsSpy,
  "candidate-efficacy": CandidateEfficacy,
  health: Health,
  "yield-curve": YieldCurve,
};

// Tiles, then the table, then any text report — all that are present, in
// that order, so a section carrying a KPI row above its rows (a source
// card's headline numbers, order-run counts) needs no dedicated component.
// Tiles with `history` points get the same sparkline the summary card's
// macro drivers use; CI columns fold into the hit-rate cell (visibleColumns)
// exactly as the dedicated track-record tables do.
function GenericSection({ sec, glossary, id }: SectionComponentProps) {
  const tiles = sec.tiles ?? [];
  const hasTable = Boolean(sec.columns && sec.rows && sec.rows.length > 0);
  const hasText = Boolean(sec.text_lines && sec.text_lines.length > 0);
  if (tiles.length === 0 && !hasTable && !hasText) return null;
  return (
    <div className="space-y-4">
      {tiles.length > 0 && (
        <div className="tiles">
          {tiles.map((tile) => (
            <StatTile key={tile.label} tile={tile}>
              {tile.history && tile.history.length >= 3 && (
                <KpiSpark label={tile.label} points={tile.history} />
              )}
            </StatTile>
          ))}
        </div>
      )}
      {hasTable && (
        <>
          <DataTable
            columns={visibleColumns(sec.columns ?? [])}
            rows={sec.rows ?? []}
            storageKey={`generic:${id ?? slug(sec.title ?? "section")}`}
            glossary={glossary}
            renderCell={makeSectionCell(sec.rows ?? [])}
          />
          {typeof sec.total === "number" && sec.total > (sec.rows?.length ?? 0) && (
            <p className="text-muted-foreground m-0 text-xs">
              showing the newest {sec.rows?.length} of {sec.total}
            </p>
          )}
        </>
      )}
      {hasText && <TextReport lines={sec.text_lines ?? []} />}
    </div>
  );
}

// Cards under ~7 rows with no tiles, text, or chart carry a narrow table
// and a wide empty right half; two of them share a row instead.
const SHORT_ROWS = 6;
function isShort(sec: Section): boolean {
  const rows = sec.rows?.length ?? 0;
  return (
    rows > 0 &&
    rows <= SHORT_ROWS &&
    !(sec.tiles?.length) &&
    !(sec.text_lines?.length) &&
    !(sec.curve?.length) &&
    !sec.columns?.some((c) => c.key === "history")
  );
}

interface StrandBodyProps {
  entries: [string, Section][];
  renderSection: (entry: [string, Section]) => ReactNode;
}

// Full cards in exporter order, then the short ones two-up (a lone
// short card renders full width — half a grid reads as a mistake; the
// h-full chain stretches each Card to the row height so paired cards'
// borders align, and min-w-0 stops a wide table from inflating its grid
// track past the viewport), then
// one "Quiet tonight" list for sections with only their empty sentence.
function StrandBody({ entries, renderSection }: StrandBodyProps) {
  const quiet = entries.filter(([, sec]) => isQuiet(sec));
  const live = entries.filter(([, sec]) => !isQuiet(sec));
  const short = live.filter(([, sec]) => isShort(sec));
  const full = live.filter(([, sec]) => !isShort(sec));
  return (
    <>
      <StrandNav entries={live} />
      {full.map(renderSection)}
      {short.length >= 2 ? (
        <div className="grid gap-4 md:grid-cols-2 [&>section]:h-full [&>section]:min-w-0 [&>section>div]:h-full">
          {short.map(renderSection)}
        </div>
      ) : (
        short.map(renderSection)
      )}
      <QuietList entries={quiet} />
    </>
  );
}

export interface MainProps {
  doc: DashboardDoc;
}

/** The strand slug the route shows, or "summary". An unknown strand slug
 * and a section id no strand holds both fall back to the Summary. */
function routedStrand(route: HashRoute, doc: DashboardDoc, labels: StrandLabel[]): string {
  if (route.route === "strand") {
    return labels.some((l) => strandId(l) === route.id) ? route.id : "summary";
  }
  if (route.route === "section") return strandOfSection(doc.sections, route.id) ?? "summary";
  return "summary";
}

interface SummaryProps {
  doc: DashboardDoc;
  labels: StrandLabel[];
}

// Tonight's plain-English read + regime chip, then one row per strand so
// the home page is also the map: what each strand holds, and the way in.
function Summary({ doc, labels }: SummaryProps) {
  const knownTickers = new Set(Object.keys(doc.tickers ?? {}));
  const regimeSec = doc.sections["regime"];
  return (
    <div className="space-y-5">
      <Card className="hero gap-4 py-5">
        <CardContent className="space-y-4 px-5">
          <div className="space-y-1.5">
            {doc.hero.bullets.map((bullet, i) => (
              <p className="read m-0 flex items-start gap-2.5 text-base" key={i}>
                <span
                  aria-hidden="true"
                  className="mt-1.5 size-2.5 shrink-0 rounded-full"
                  style={{ background: TONE_DOT[bullet.tone] }}
                />
                <span>{linkifyTickers(bullet.text, knownTickers)}</span>
              </p>
            ))}
          </div>
          {regimeSec?.verdict && (
            <>
              <Separator />
              {/* The regime chip alone: the deciding inputs render as the
                  macro-drivers card in Macro, beside the table they explain. */}
              <VerdictChip verdict={regimeSec.verdict} className="text-sm" />
            </>
          )}
        </CardContent>
      </Card>

      <nav aria-label="strand index" className="strand-index">
        <ItemGroup className="grid gap-3 md:grid-cols-2">
          {labels.map((label) => (
            <Item key={label} asChild variant="outline" size="sm" className="no-underline">
              <a href={`#/${strandId(label)}`}>
                <ItemContent>
                  <ItemTitle>{label}</ItemTitle>
                  <ItemDescription>{STRAND_BLURBS[label]}</ItemDescription>
                </ItemContent>
                <ItemActions>
                  <ChevronRight aria-hidden="true" className="text-muted-foreground size-4" />
                </ItemActions>
              </a>
            </Item>
          ))}
        </ItemGroup>
      </nav>
    </div>
  );
}

export function Main({ doc }: MainProps) {
  const glossary = doc.glossary ?? {};
  const route = useHashRoute();
  const labels = strandLabels(doc.sections);
  const active = routedStrand(route, doc, labels);

  // A section anchor lands after its strand is shown (the strand is hidden
  // until this render, so the browser's own hash scroll found nothing).
  // Strand switches start from the top — the hash changed but no element
  // matches it, so the viewport would otherwise stay wherever it was.
  useEffect(() => {
    if (route.route === "section") {
      document.getElementById(route.id)?.scrollIntoView?.({ block: "start" });
    } else {
      window.scrollTo(0, 0);
    }
  }, [route]);

  function renderSection([id, sec]: [string, Section]) {
    const Component = SECTION_COMPONENTS[id] ?? GenericSection;
    return (
      <SectionShell key={id} id={id} sec={sec}>
        <Component sec={sec} glossary={glossary} id={id} />
      </SectionShell>
    );
  }

  return (
    <div>
      {active === "summary" && <Summary doc={doc} labels={labels} />}

      {labels.map((label) => {
        const slug = strandId(label);
        const state = active === slug ? "active" : "inactive";
        return (
          <section
            key={label}
            id={slug}
            aria-label={label}
            data-state={state}
            className="strand space-y-4 data-[state=inactive]:hidden"
          >
            <h2 className="sr-only">{label}</h2>
            <StrandBody entries={strandSections(doc.sections, label)} renderSection={renderSection} />
          </section>
        );
      })}

      {/* Ledger colophon: generation timestamp in the READER's local time
          (the raw export is UTC; the masthead's edition date is the Phoenix
          trading date, not the run time) + source link. */}
      <footer className="colophon text-muted-foreground mt-8 text-xs">
        Generated {formatGeneratedAt(doc.generated_at)} ·{" "}
        <ExtLink href={REPO_URL}>source</ExtLink>
      </footer>
    </div>
  );
}
