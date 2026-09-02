// Parses `location.hash` into a route without pulling in a router
// dependency. Four shapes:
//   `#` / `#/`            main (the Summary page)
//   `#/ticker/<SYMBOL>`   per-ticker drill-down
//   `#/<slug>`            a strand page (`#/macro`, `#/track-record`)
//   `#<section-id>`       a bare section anchor — StrandNav and hero links
//                         address sections this way; Main resolves it to
//                         the strand that holds the section and scrolls.

import { useEffect, useState } from "react";

export type HashRoute =
  | { route: "main" }
  | { route: "ticker"; symbol: string }
  | { route: "strand"; id: string }
  | { route: "section"; id: string };

const TICKER_RE = /^#\/ticker\/([^/]+)\/?$/;
const STRAND_RE = /^#\/([^/]+)\/?$/;
const SECTION_RE = /^#([^/]+)$/;

function parseHash(hash: string): HashRoute {
  const ticker = TICKER_RE.exec(hash);
  if (ticker) return { route: "ticker", symbol: decodeURIComponent(ticker[1]) };
  const strand = STRAND_RE.exec(hash);
  if (strand) return { route: "strand", id: decodeURIComponent(strand[1]) };
  const section = SECTION_RE.exec(hash);
  if (section) return { route: "section", id: decodeURIComponent(section[1]) };
  return { route: "main" };
}

export function useHashRoute(): HashRoute {
  const [route, setRoute] = useState<HashRoute>(() => parseHash(location.hash));

  useEffect(() => {
    function onHashChange(): void {
      setRoute(parseHash(location.hash));
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return route;
}
