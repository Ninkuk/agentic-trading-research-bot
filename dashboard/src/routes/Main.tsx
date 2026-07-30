// The main page: masthead -> "Tonight in plain English" hero -> KPI tile
// row -> five strands (Macro / Signals / Research / Track record / Your
// book), each section wrapped in SectionShell.
//
// `SECTION_COMPONENTS` maps a section id to the component that renders its
// body; a section id with no entry falls back to `GenericSection` (columns+
// rows through DataTable, tiles through StatTile, text_lines through
// <pre>) so a section the Python exporter adds before its React component
// ships never renders blank. Every registered/fallback component takes
// exactly `{sec, glossary}` — the pattern Task 14's remaining sections
// follow.
//
// Strand grouping comes from each section's own `kicker` field (already
// "Macro"/"Signals"/.../"Your book" per data.py's SECTION_EXPORTERS), not a
// hardcoded id list — a section moving strands in Python needs no frontend
// change. The five strand headings render unconditionally in a fixed order
// even when a given night's document has no section for one (e.g. no
// research-reopens entry yet), because StrandNav always offers all five.
// `KICKERS`' compile-time union can't validate a live JSON payload (JSON
// always reads back as plain `string`), so any section whose kicker isn't
// one of the five known strands — a rename, a typo, a brand-new kicker the
// frontend hasn't caught up to yet — still renders, in a trailing "Other"
// group, rather than silently vanishing.

import type { ComponentType } from "react";
import { Sparkline } from "../charts/Sparkline";
import { signed } from "../format";
import { MacroDrivers } from "../sections/MacroDrivers";
import { Regime } from "../sections/Regime";
import { RegimeTimelineSection } from "../sections/RegimeTimelineSection";
import { KICKERS, type DashboardDoc, type Glossary, type Section } from "../types";
import { DataTable } from "../ui/DataTable";
import { Masthead } from "../ui/Masthead";
import { SectionShell } from "../ui/SectionShell";
import { StatTile } from "../ui/StatTile";
import { StrandNav } from "../ui/StrandNav";
import { VerdictChip } from "../ui/VerdictChip";

interface SectionComponentProps {
  sec: Section;
  glossary: Glossary;
  // Registered components (Regime, RegimeTimelineSection, MacroDrivers) may
  // ignore this — only GenericSection needs it, for a storageKey that
  // survives a section title rename/duplicate.
  id?: string;
}

const STRAND_SET = new Set<string>(KICKERS);

function strandId(label: string): string {
  return label.toLowerCase().replace(/\s+/g, "-");
}

function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

const SECTION_COMPONENTS: Record<string, ComponentType<SectionComponentProps>> = {
  regime: Regime,
  "regime-timeline": RegimeTimelineSection,
  "macro-drivers": MacroDrivers,
};

function GenericSection({ sec, glossary, id }: SectionComponentProps) {
  if (sec.columns && sec.rows) {
    return (
      <DataTable
        columns={sec.columns}
        rows={sec.rows}
        storageKey={`generic:${id ?? slug(sec.title ?? "section")}`}
        glossary={glossary}
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
    return <pre>{sec.text_lines.join("\n")}</pre>;
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

  return (
    <div className="page">
      <Masthead editionDate={doc.edition_date} snapshotNumber={doc.snapshot_number} />

      <StrandNav strands={KICKERS.map((label) => ({ id: strandId(label), label }))} />

      <div className="hero">
        <p className="eyebrow">Tonight in plain English</p>
        {doc.hero.bullets.map((bullet, i) => (
          <p className="read" key={i}>
            <b className={bullet.tone}>{bullet.text}</b>
          </p>
        ))}
      </div>

      <div className="tiles kpi-row">
        {regimeSec?.verdict && <VerdictChip verdict={regimeSec.verdict} />}
        {(macroSec?.tiles ?? []).map((tile) => (
          <StatTile key={tile.label} tile={tile}>
            {typeof tile.delta === "number" && <span className="d">{signed(tile.delta)}</span>}
            {tile.history && tile.history.length >= 2 && <Sparkline points={tile.history} tone="hold" />}
          </StatTile>
        ))}
      </div>

      {KICKERS.map((label) => {
        const strandSections = entries.filter(([, sec]) => sec.kicker === label);
        return (
          <section key={label} id={strandId(label)} className="strand">
            <h2 className="strand-heading">{label}</h2>
            {strandSections.map(renderSection)}
          </section>
        );
      })}

      {otherSections.length > 0 && (
        <section id="other" className="strand">
          <h2 className="strand-heading">Other</h2>
          {otherSections.map(renderSection)}
        </section>
      )}
    </div>
  );
}
