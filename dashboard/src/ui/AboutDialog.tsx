// The per-section "About" modal: an info-icon trigger in the card header
// opening the section's long-form explainer as headed blocks. The card
// itself keeps only the one-sentence `note` — everything longer (reading
// mechanics, failure modes, trust caveats) lives here, so the explainers
// can be thorough without turning every card header into a wall of text.
// Renders nothing when a section has no about blocks (e.g. a degraded
// document from an older data.json) — never a dead trigger.

import { Info } from "lucide-react";
import type { AboutBlock } from "../types";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";

export interface AboutDialogProps {
  title: string;
  about?: AboutBlock[];
}

export function AboutDialog({ title, about }: AboutDialogProps) {
  if (!about || about.length === 0) return null;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground size-7"
          aria-label={`About ${title}`}
        >
          <Info aria-hidden="true" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {about.map((block) => (
            <section key={block.heading}>
              <h3 className="m-0 mb-1 text-sm font-semibold">{block.heading}</h3>
              <p className="text-muted-foreground m-0 text-sm">{block.body}</p>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
