// A sticky pill row of in-strand anchors, for strands long enough that
// the card titles alone don't help you find a feed (Sources: 31 cards).
// Sticky under the viewport top; scroll-mt on the sections keeps the
// target title from landing under it.

import type { Section, SectionId } from "../types";

export interface StrandNavProps {
  entries: [SectionId, Section][];
}

export function StrandNav({ entries }: StrandNavProps) {
  if (entries.length < 8) return null;
  return (
    <nav
      aria-label="sections in this strand"
      className="strand-nav bg-background/95 sticky top-0 z-10 -mx-1 flex flex-wrap gap-1.5 px-1 py-2 backdrop-blur"
    >
      {entries.map(([id, sec]) => (
        <a
          key={id}
          href={`#${id}`}
          className="text-muted-foreground hover:text-foreground hover:bg-muted rounded-full border px-2.5 py-0.5 text-xs no-underline"
        >
          {sec.title ?? id}
        </a>
      ))}
    </nav>
  );
}
