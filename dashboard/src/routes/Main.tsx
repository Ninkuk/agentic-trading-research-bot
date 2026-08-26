// The main page: masthead -> combined summary card ("Tonight in plain
// English" bullets + regime chip + macro-driver KPIs with sparklines) ->
// the seven strands as tabs, each section rendered in a SectionShell card.
//
// `SECTION_COMPONENTS` maps a section id to the component that renders its
// body; a section id with no entry falls back to `GenericSection` (columns+
// rows through DataTable, tiles through StatTile, text_lines through
// TextReport) so a section the Python exporter adds before its React
// component ships never renders blank. Every registered/fallback component
// takes exactly `{sec, glossary}`.
//
// Strand grouping comes from each section's own `kicker` field (already
// "Macro"/"Signals"/.../"Your book" per data.py's SECTION_EXPORTERS), not a
// hardcoded id list — a section moving strands in Python needs no frontend
// change. The seven strand tabs render unconditionally in a fixed order even
// when a given night's document has no section for one. Any section whose
// kicker isn't a known strand — a rename, a typo, a brand-new kicker the
// frontend hasn't caught up to yet — still renders, in a trailing "Other"
// tab, rather than silently vanishing.
//
// Tab contents are force-mounted (hidden when inactive) so in-page find,
// anchor links to section ids, and DOM-querying tests all see the whole
// document; only visibility toggles.
//
// macro-drivers is the one section not repeated inside its strand: the
// summary card at the top IS its rendering (tiles + sparklines).

import type { ComponentType, ReactNode } from "react";
import { KpiSpark } from "../charts/KpiSpark";
import { REPO_URL } from "../constants";
import { ExtLink } from "../ui/ExtLink";
import { signed } from "../format";
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
import { TraderScorecard } from "../sections/TraderScorecard";
import { KICKERS, type DashboardDoc, type Glossary, type Section, type Tone } from "../types";
import { Card, CardContent } from "../components/ui/card";
import { Separator } from "../components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { DataTable } from "../ui/DataTable";
import { Masthead } from "../ui/Masthead";
import { SectionShell } from "../ui/SectionShell";
import { sectionCell, visibleColumns } from "../ui/sectionCells";
import { StatTile } from "../ui/StatTile";
import { TextReport } from "../ui/TextReport";
import { VerdictChip } from "../ui/VerdictChip";

interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  id?: string;
}

const STRAND_SET = new Set<string>(KICKERS);

// Rendered in the summary card, not inside its strand tab.
const HEADER_SECTIONS = new Set(["macro-drivers"]);

const TONE_DOT: Record<Tone, string> = {
  on: "var(--tone-up)",
  off: "var(--tone-down)",
  mid: "var(--tone-hold)",
};

function strandId(label: string): string {
  return label.toLowerCase().replace(/\s+/g, "-");
}

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

// macro-drivers has no entry: it renders in the summary card (see
// HEADER_SECTIONS); if its kicker ever stops matching, GenericSection's
// tiles path still covers it.
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
            renderCell={sectionCell}
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

export interface MainProps {
  doc: DashboardDoc;
}

export function Main({ doc }: MainProps) {
  const glossary = doc.glossary ?? {};
  const knownTickers = new Set(Object.keys(doc.tickers ?? {}));
  const entries = Object.entries(doc.sections);
  const regimeSec = doc.sections["regime"];
  const macroSec = doc.sections["macro-drivers"];

  function renderSection([id, sec]: [string, Section]) {
    const Component = SECTION_COMPONENTS[id] ?? GenericSection;
    return (
      <SectionShell key={id} id={id} sec={sec}>
        <Component sec={sec} glossary={glossary} id={id} />
      </SectionShell>
    );
  }

  const otherSections = entries.filter(([, sec]) => !sec.kicker || !STRAND_SET.has(sec.kicker));
  const tabLabels: string[] = [...KICKERS, ...(otherSections.length > 0 ? ["Other"] : [])];

  function strandSections(label: string): [string, Section][] {
    if (label === "Other") return otherSections;
    return entries.filter(([id, sec]) => sec.kicker === label && !HEADER_SECTIONS.has(id));
  }

  return (
    <div className="page">
      <Masthead editionDate={doc.edition_date} snapshotNumber={doc.snapshot_number} />

      {/* Summary card: tonight's plain-English read + regime chip + macro
          KPIs — the hero and the old KPI row merged into one block. */}
      <Card className="hero mb-5 gap-4 py-5">
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
          {(regimeSec?.verdict || (macroSec?.tiles ?? []).length > 0) && (
            <>
              <Separator />
              {/* id="macro-drivers": this row IS that section's rendering
                  (see HEADER_SECTIONS) — the anchor stays addressable.
                  Lab Variant C's KPI anatomy: label above a mono value with
                  the delta inline, sparkline to the right. */}
              <div id="macro-drivers" className="kpi-row flex flex-wrap items-center gap-x-8 gap-y-3">
                {regimeSec?.verdict && (
                  <VerdictChip verdict={regimeSec.verdict} className="text-sm" />
                )}
                {(macroSec?.tiles ?? []).map((tile) => (
                  <div key={tile.label} className="tile flex items-center gap-3">
                    <div>
                      <div className="text-muted-foreground text-xs">{tile.label}</div>
                      <div className="font-mono text-base leading-tight font-semibold tabular-nums">
                        {typeof tile.value === "number" ? tile.value : String(tile.value ?? "—")}
                        {typeof tile.delta === "number" && (
                          <span className="text-muted-foreground ml-1.5 text-xs font-normal">
                            {signed(tile.delta)}
                          </span>
                        )}
                      </div>
                    </div>
                    {tile.history && <KpiSpark label={tile.label} points={tile.history} />}
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue={strandId(KICKERS[0])}>
        {/* justify-start + overflow-x-auto: six triggers don't fit a phone
            width, and TabsTrigger never shrinks below its label — without a
            scroll container the strip widens the whole document (the
            "Macro" → "cro" bug). Desktop is unaffected: flex-1 triggers
            still fill the full width. */}
        <TabsList className="w-full justify-start overflow-x-auto [scrollbar-width:none]">
          {tabLabels.map((label) => (
            <TabsTrigger key={label} value={strandId(label)}>
              {label}
            </TabsTrigger>
          ))}
        </TabsList>
        {tabLabels.map((label) => (
          <TabsContent
            key={label}
            value={strandId(label)}
            forceMount
            className="strand space-y-4 pt-2 data-[state=inactive]:hidden"
            id={strandId(label)}
          >
            {strandSections(label).map(renderSection)}
          </TabsContent>
        ))}
      </Tabs>

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
