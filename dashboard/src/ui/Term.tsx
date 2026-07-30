// A dotted-underline glossary term: click or hover opens a positioned
// popover with the definition. Terms missing from the glossary render as
// plain text — never a dead-looking underline promising a definition that
// isn't there (see the brief: "renders plain children when the term is
// missing from the glossary").

import { useEffect, useId, useState, type ReactNode } from "react";
import type { Glossary } from "../types";

export interface TermProps {
  term: string;
  glossary: Glossary;
  children: ReactNode;
}

export function Term({ term, glossary, children }: TermProps) {
  const definition = glossary[term];
  const [open, setOpen] = useState(false);
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

  return (
    <span className="term">
      <button
        type="button"
        className="term-trigger"
        aria-expanded={open}
        aria-describedby={open ? popoverId : undefined}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        {children}
      </button>
      {open && (
        <span id={popoverId} role="tooltip" className="jstip term-popover">
          {definition}
        </span>
      )}
    </span>
  );
}
