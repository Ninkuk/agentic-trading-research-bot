// A dotted-underline glossary term: click or hover opens a positioned
// popover with the definition. Terms missing from the glossary render as
// plain text — never a dead-looking underline promising a definition that
// isn't there (see the brief: "renders plain children when the term is
// missing from the glossary").
//
// The popover portals to document.body: most triggers live inside the
// shadcn table's `overflow-x: auto` wrapper, which clips an absolutely
// positioned tooltip invisible. Fixed positioning from the trigger's
// viewport rect escapes the clip; the popover flips below the trigger when
// there isn't room above.

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { Glossary } from "../types";

export interface TermProps {
  term: string;
  glossary: Glossary;
  children: ReactNode;
}

/** Matches .jstip's max-width plus a little viewport margin. */
const POPOVER_WIDTH = 270;
/** Rough room needed above the trigger before flipping below. */
const FLIP_THRESHOLD = 140;

interface PopoverPos {
  left: number;
  top: number;
  below: boolean;
}

export function Term({ term, glossary, children }: TermProps) {
  const definition = glossary[term];
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<PopoverPos | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverId = useId();

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent): void {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (definition === undefined) {
    return <>{children}</>;
  }

  function show(): void {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      const below = rect.top < FLIP_THRESHOLD;
      setPos({
        left: Math.max(8, Math.min(rect.left, window.innerWidth - POPOVER_WIDTH)),
        top: below ? rect.bottom + 6 : rect.top - 6,
        below,
      });
    } else {
      setPos(null);
    }
    setOpen(true);
  }

  return (
    <span className="term">
      <button
        ref={triggerRef}
        type="button"
        className="term-trigger"
        aria-expanded={open}
        aria-describedby={open ? popoverId : undefined}
        onClick={(e) => {
          e.stopPropagation();
          show();
        }}
        onMouseEnter={show}
        onMouseLeave={() => setOpen(false)}
        onBlur={() => setOpen(false)}
      >
        {children}
      </button>
      {open &&
        createPortal(
          <span
            id={popoverId}
            role="tooltip"
            className="jstip term-popover"
            style={
              pos
                ? {
                    position: "fixed",
                    left: pos.left,
                    top: pos.top,
                    bottom: "auto",
                    transform: pos.below ? undefined : "translateY(-100%)",
                  }
                : undefined
            }
          >
            {definition}
          </span>,
          document.body,
        )}
    </span>
  );
}
