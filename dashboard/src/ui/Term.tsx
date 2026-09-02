// A dotted-underline glossary term: click or hover opens a popover with
// the definition. Terms missing from the glossary render as plain text —
// never a dead-looking underline promising a definition that isn't there
// (see the brief: "renders plain children when the term is missing from
// the glossary").
//
// shadcn Popover: it portals to document.body (most triggers live inside
// the table's `overflow-x: auto` wrapper, which clips an in-flow popover)
// and flips below the trigger when there isn't room above. Open state is
// controlled so hover drives it beside click; the click handler prevents
// Radix's default toggle so a click always shows (Escape and an outside
// click close), and auto-focus is off both ways so a hover-open never
// moves keyboard focus. `role="tooltip"`: the content is a definition, not
// a dialog to act in.

import { useState, type ReactNode } from "react";
import type { Glossary } from "../types";
import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";

export interface TermProps {
  term: string;
  glossary: Glossary;
  children: ReactNode;
}

export function Term({ term, glossary, children }: TermProps) {
  const definition = glossary[term];
  const [open, setOpen] = useState(false);

  if (definition === undefined) {
    return <>{children}</>;
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="term-trigger"
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
            setOpen(true);
          }}
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          {children}
        </button>
      </PopoverTrigger>
      <PopoverContent
        role="tooltip"
        side="top"
        align="start"
        sideOffset={6}
        className="term-popover w-auto max-w-[270px] px-2.5 py-1.5 text-xs leading-normal font-normal"
        onOpenAutoFocus={(e) => e.preventDefault()}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        {definition}
      </PopoverContent>
    </Popover>
  );
}
