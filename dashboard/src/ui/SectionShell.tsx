// The ledger-style wrapper every section renders inside: a margin-note
// gutter (kicker/title/verdict/intro prose/caveat) plus a data column
// (children). A per-section collapse toggle persists via
// usePrefs(`collapse:${id}`) — collapsed shows the header row (title +
// verdict chip) only. Error and empty states render inside the shell so a
// degraded section (missing DB, zero rows) still looks like part of the
// page rather than a broken hole in it.

import type { ReactNode } from "react";
import { usePrefs } from "../hooks/usePrefs";
import type { Section, SectionId } from "../types";
import { CaveatLine } from "./CaveatLine";
import { VerdictChip } from "./VerdictChip";

export interface SectionShellProps {
  id: SectionId;
  sec: Section;
  collapsible?: boolean;
  children?: ReactNode;
}

export function SectionShell({ id, sec, collapsible = true, children }: SectionShellProps) {
  const [collapsed, setCollapsed] = usePrefs<boolean>(`collapse:${id}`, false);

  const hasRows = Array.isArray(sec.rows) && sec.rows.length > 0;
  const showEmpty = !sec.error && sec.empty !== undefined && !hasRows;

  return (
    <section className="ledger" id={id}>
      <div className="note">
        {sec.kicker && <p className="kicker">{sec.kicker}</p>}
        <div className="section-header-row">
          {sec.title && <h2>{sec.title}</h2>}
          {sec.verdict && <VerdictChip verdict={sec.verdict} />}
          {collapsible && (
            <button
              type="button"
              className="collapse-toggle"
              aria-expanded={!collapsed}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? "expand" : "collapse"}
            </button>
          )}
        </div>
        {!collapsed && sec.note && <p>{sec.note}</p>}
      </div>
      {!collapsed && (
        <div className="data">
          {sec.error ? (
            <p className="unavailable">{sec.error}</p>
          ) : showEmpty ? (
            <p className="empty">{sec.empty}</p>
          ) : (
            children
          )}
          {sec.caveat && <CaveatLine text={sec.caveat} />}
        </div>
      )}
    </section>
  );
}
