// The one-sentence degraded state (no rows, no history, still loading):
// the shadcn Empty composition with a leading icon, so every "nothing
// here" on the page reads the same way. `loading` swaps the icon for a
// spinner; `icon` overrides it (Health's all-clear is a check, not an
// inbox).

import { Inbox, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia } from "../components/ui/empty";
import { Spinner } from "../components/ui/spinner";

export interface EmptyNoteProps {
  children: ReactNode;
  loading?: boolean;
  icon?: LucideIcon;
}

export function EmptyNote({ children, loading = false, icon: Icon = Inbox }: EmptyNoteProps) {
  return (
    <Empty className="empty-note border border-dashed py-6 md:py-8">
      <EmptyHeader>
        <EmptyMedia variant="icon">{loading ? <Spinner /> : <Icon aria-hidden="true" />}</EmptyMedia>
        <EmptyDescription>{children}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
