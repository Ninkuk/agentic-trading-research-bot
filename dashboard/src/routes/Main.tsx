// The main page: masthead -> combined summary card ("Tonight in plain
// English" bullets + regime chip + macro-driver KPIs with sparklines) ->
// the five strands as tabs, each section rendered in a SectionShell card.
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
// change. The five strand tabs render unconditionally in a fixed order even
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

import type { ComponentType } from "react";
import { KpiSpark } from "../charts/KpiSpark";
import { REPO_URL } from "../constants";
import { signed } from "../format";
import { BasisBreaks } from "../sections/BasisBreaks";
import { BookHeat } from "../sections/BookHeat";
import { BucketPerformance } from "../sections/BucketPerformance";
import { CandidateEfficacy } from "../sections/CandidateEfficacy";
import { Candidates } from "../sections/Candidates";
import { Disagreements } from "../sections/Disagreements";
import { GroupHeat } from "../sections/GroupHeat";
import { HumanFilter } from "../sections/HumanFilter";
import { Pending } from "../sections/Pending";
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
import { sectionCell } from "../ui/sectionCells";
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

function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
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
  "plan-001-report": SignalRecommendations,
  "plan-004-scorecard": TraderScorecard,
  "candidate-efficacy": CandidateEfficacy,
};

function GenericSection({ sec, glossary, id }: SectionComponentProps) {
  if (sec.columns && sec.rows) {
    return (
      <DataTable
        columns={sec.columns}
        rows={sec.rows}
        storageKey={`generic:${id ?? slug(sec.title ?? "section")}`}
        glossary={glossary}
        renderCell={sectionCell}
      />
    );
  }
  if (sec.tiles && sec.tiles.length > 0) {
    return (
      <div className="tiles">
        {sec.tiles.map((tile) => (
          <StatTile key={tile.label} tile={tile} />
        ))}
      </div>
    );
  }
  if (sec.text_lines && sec.text_lines.length > 0) {
    return <TextReport lines={sec.text_lines} />;
  }
  return null;
}

export interface MainProps {
  doc: DashboardDoc;
}

export function Main({ doc }: MainProps) {
  const glossary = doc.glossary ?? {};
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
              <p className="read m-0 flex items-start gap-2.5 text-[15px]" key={i}>
                <span
                  aria-hidden="true"
                  className="mt-1.5 size-2.5 shrink-0 rounded-full"
                  style={{ background: TONE_DOT[bullet.tone] }}
                />
                {bullet.text}
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
                      <div className="text-muted-foreground text-[11px]">{tile.label}</div>
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
        <TabsList className="w-full">
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

      {/* Ledger colophon: exact generation timestamp (the masthead's edition
          date is the Phoenix trading date, not the run time) + source link. */}
      <footer className="colophon text-muted-foreground mt-8 text-xs">
        Generated {doc.generated_at.replace("T", " ").replace("+00:00", " UTC")} ·{" "}
        <a href={REPO_URL} target="_blank" rel="noreferrer">
          source
        </a>
      </footer>
    </div>
  );
}
