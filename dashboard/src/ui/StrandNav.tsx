// Sticky nav across the five strands, with IntersectionObserver-driven
// scroll-spy highlighting whichever strand is currently in view (stubbed
// in tests — vitest.setup.ts installs a no-op IntersectionObserver, so the
// observer never actually fires there; only the render + click contract is
// tested). Clicking a link smooth-scrolls to that strand's section and
// sets location.hash explicitly (belt-and-suspenders: scrollIntoView isn't
// implemented in jsdom, and setting the hash ourselves means it's correct
// even if the browser's native anchor-jump is interrupted mid-scroll).

import { useEffect, useState, type MouseEvent } from "react";

export interface StrandNavItem {
  id: string;
  label: string;
}

export interface StrandNavProps {
  strands: StrandNavItem[];
}

export function StrandNav({ strands }: StrandNavProps) {
  const [activeId, setActiveId] = useState<string | undefined>(strands[0]?.id);

  useEffect(() => {
    const elements = strands
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);
    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length > 0) setActiveId(visible[0].target.id);
      },
      { rootMargin: "-10% 0px -80% 0px" },
    );
    for (const el of elements) observer.observe(el);
    return () => observer.disconnect();
  }, [strands]);

  function handleClick(e: MouseEvent<HTMLAnchorElement>, id: string): void {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView?.({ behavior: "smooth" });
    location.hash = id;
    setActiveId(id);
  }

  return (
    <nav className="jump strand-nav" aria-label="Strands">
      {strands.map((s) => (
        <a
          key={s.id}
          href={`#${s.id}`}
          className={s.id === activeId ? "active" : undefined}
          onClick={(e) => handleClick(e, s.id)}
        >
          {s.label}
        </a>
      ))}
    </nav>
  );
}
