// The card every section renders inside: title + note (the old margin-note
// prose, now the card description directly under the title) + verdict chip
// in the header's action slot, data as children. The strand tab in Main.tsx
// already labels each group, so `sec.kicker` stays a grouping field only
// and is not rendered here. Error and empty states render inside the shell
// so a degraded section (missing DB, zero rows) still looks like part of
// the page rather than a broken hole in it.

import type { ReactNode } from "react";
import { CircleAlert, Inbox } from "lucide-react";
import type { Section, SectionId } from "../types";
import { Card, CardAction, CardContent, CardHeader } from "../components/ui/card";
import { CaveatLine } from "./CaveatLine";
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
          {sec.title && <h2 className="m-0 text-base leading-none font-semibold">{sec.title}</h2>}
          {sec.note && <p className="text-muted-foreground m-0 text-sm">{sec.note}</p>}
          {sec.verdict && (
            <CardAction>
              <VerdictChip verdict={sec.verdict} />
            </CardAction>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {sec.error ? (
            <p className="unavailable">
              <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span>{sec.error}</span>
            </p>
          ) : showEmpty ? (
            <p className="empty">
              <Inbox className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span>{sec.empty}</span>
            </p>
          ) : (
            children
          )}
          {sec.caveat && <CaveatLine text={sec.caveat} />}
        </CardContent>
      </Card>
    </section>
  );
}
