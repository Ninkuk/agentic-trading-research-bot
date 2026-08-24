// An outbound link that reads as one without hovering: the quiet underline
// symbol links use plus an out-arrow icon. Bare words like "thesis" or
// "source" gave no cue they left the app. Always a new tab — the dashboard
// is a single hash-routed page and a same-tab GitHub jump loses its state.

import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";

export function ExtLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a className="ext-link" href={href} target="_blank" rel="noreferrer">
      {children}
      <ExternalLink aria-hidden="true" className="ext-link-icon" />
    </a>
  );
}
