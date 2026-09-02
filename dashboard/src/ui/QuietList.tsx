// oxlint-disable react/only-export-components -- isQuiet is the strand
// partition rule that Main.tsx applies before choosing this list.
// The strand's "Quiet tonight" card: sections whose body is only their
// `empty` sentence collapse to one row each (a shadcn Item) instead of a
// full card, so a strand's height reflects what it has to say. Each row
// keeps the section id as an anchor and its About trigger — nothing
// becomes unreachable.

import { Inbox } from "lucide-react";
import type { Section, SectionId } from "../types";
import { Card, CardContent, CardHeader } from "../components/ui/card";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from "../components/ui/item";
import { AboutDialog } from "./AboutDialog";

export interface QuietListProps {
  entries: [SectionId, Section][];
}

/** A section belongs in the quiet list when it has no rows, no tiles, no
 * text, no chart data, and no error — just its empty sentence. */
export function isQuiet(sec: Section): boolean {
  if (sec.error || sec.empty === undefined) return false;
  const hasRows = Array.isArray(sec.rows) && sec.rows.length > 0;
  const hasTiles = Array.isArray(sec.tiles) && sec.tiles.length > 0;
  const hasText = Array.isArray(sec.text_lines) && sec.text_lines.length > 0;
  const hasCurve = Array.isArray(sec.curve) && sec.curve.length > 0;
  return !hasRows && !hasTiles && !hasText && !hasCurve;
}

export function QuietList({ entries }: QuietListProps) {
  if (entries.length === 0) return null;
  return (
    <Card className="quiet-list">
      <CardHeader>
        <h2 className="m-0 text-lg leading-none font-semibold">Quiet tonight</h2>
        <p className="text-muted-foreground m-0 max-w-[75ch] text-sm">
          Sections with nothing to show this run.
        </p>
      </CardHeader>
      <CardContent>
        <ul className="m-0 list-none divide-y p-0">
          {entries.map(([id, sec]) => (
            <Item key={id} asChild size="sm" className="ledger scroll-mt-16 rounded-none px-0">
              <li id={id}>
                <ItemMedia variant="icon">
                  <Inbox aria-hidden="true" />
                </ItemMedia>
                <ItemContent>
                  <ItemTitle>{sec.title}</ItemTitle>
                  <ItemDescription>{sec.empty}</ItemDescription>
                </ItemContent>
                <ItemActions>
                  <AboutDialog title={sec.title ?? "About this section"} about={sec.about} />
                </ItemActions>
              </li>
            </Item>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
