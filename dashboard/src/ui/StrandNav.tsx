// A sticky chip row of in-strand anchors, one per publisher group, shown
// below `lg` only: there the sidebar is an offcanvas sheet that closes on
// navigation, so this is the in-page map. On desktop the rail lists the
// same items under the expanded strand (AppShell). One chip per group
// fits a line where a chip per card wrapped to four; the group holding
// the topmost visible card carries aria-current. Sticky under the
// viewport top; scroll-mt on the sections and headings keeps the target
// from landing under it.

import { useScrollSpy } from "../hooks/useScrollSpy";
import type { SectionGroup } from "../strands";

export interface StrandNavProps {
  groups: SectionGroup[];
}

export function StrandNav({ groups }: StrandNavProps) {
  const groupOf = new Map<string, string>();
  for (const g of groups)
    for (const [id] of g.entries) groupOf.set(id, g.anchor);
  const visible = useScrollSpy(Array.from(groupOf.keys()));
  const current = visible ? (groupOf.get(visible) ?? null) : null;

  return (
    <nav
      aria-label="sections in this strand"
      className="strand-nav bg-background/95 sticky top-0 z-10 -mx-1 flex flex-wrap gap-1.5 px-1 py-2 backdrop-blur lg:hidden"
    >
      {groups.map((g) => (
        <a
          key={g.anchor}
          href={`#${g.anchor}`}
          aria-current={current === g.anchor ? "location" : undefined}
          className="text-muted-foreground hover:text-foreground hover:bg-muted aria-[current]:bg-muted aria-[current]:text-foreground aria-[current]:border-foreground/30 rounded-full border px-2.5 py-0.5 text-xs no-underline"
        >
          {g.label}
        </a>
      ))}
    </nav>
  );
}
