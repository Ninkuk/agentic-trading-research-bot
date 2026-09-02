// The card every section renders inside: title + note (a one-sentence
// essence as the card description) + the About modal trigger and verdict
// chip in the header's action slot, data as children. The long-form
// explainer lives in the About modal (AboutDialog, sec.about blocks) — the
// card never carries more than the one-liner. The strand tab in Main.tsx
// already labels each group, so `sec.kicker` stays a grouping field only
// and is not rendered here. Error and empty states render inside the shell
// so a degraded section (missing DB, zero rows) still looks like part of
// the page rather than a broken hole in it.

import type { ReactNode } from "react";
import { CircleAlert } from "lucide-react";
import type { Section, SectionId } from "../types";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Card, CardAction, CardContent, CardHeader } from "../components/ui/card";
import { AboutDialog } from "./AboutDialog";
import { CaveatLine } from "./CaveatLine";
import { EmptyNote } from "./EmptyNote";
import { VerdictChip } from "./VerdictChip";

export interface SectionShellProps {
  id: SectionId;
  sec: Section;
  children?: ReactNode;
}

export function SectionShell({ id, sec, children }: SectionShellProps) {
  const hasRows = Array.isArray(sec.rows) && sec.rows.length > 0;
  const showEmpty = !sec.error && sec.empty !== undefined && !hasRows;

  return (
    <section className="ledger scroll-mt-16" id={id}>
      <Card>
        <CardHeader>
          {/* text-lg: a real step over 14px body (1.29 ratio) — at text-base
              the whole page read as one flat size. */}
          {sec.title && <h2 className="m-0 text-lg leading-none font-semibold">{sec.title}</h2>}
          {/* max-w keeps the note at a readable measure — the card itself is
              as wide as the page (72rem), which is far too wide for prose. */}
          {sec.note && (
            <p className="text-muted-foreground m-0 max-w-[75ch] text-sm">{sec.note}</p>
          )}
          {(sec.verdict || (sec.about && sec.about.length > 0)) && (
            /* On phones the action slot stops sharing a row with the note —
               a side-by-side grid squeezes the one-sentence note into a
               ~130px column while the right half sits empty. */
            <CardAction className="flex items-center gap-1 max-sm:col-start-1 max-sm:row-span-1 max-sm:row-start-3 max-sm:justify-self-start">
              {sec.verdict && <VerdictChip verdict={sec.verdict} />}
              <AboutDialog title={sec.title ?? "About this section"} about={sec.about} />
            </CardAction>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {sec.error ? (
            <Alert variant="destructive">
              <CircleAlert />
              <AlertDescription className="font-mono">{sec.error}</AlertDescription>
            </Alert>
          ) : showEmpty ? (
            <EmptyNote>{sec.empty}</EmptyNote>
          ) : (
            children
          )}
          {sec.caveat && <CaveatLine text={sec.caveat} />}
        </CardContent>
      </Card>
    </section>
  );
}
