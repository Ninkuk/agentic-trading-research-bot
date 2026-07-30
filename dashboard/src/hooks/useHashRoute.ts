// Parses `location.hash` into a route without pulling in a router
// dependency — the dashboard has exactly two destinations: the main page
// and a per-ticker detail view addressed as `#/ticker/<SYMBOL>`.

import { useEffect, useState } from "react";

export type HashRoute = { route: "main" } | { route: "ticker"; symbol: string };

const TICKER_RE = /^#\/ticker\/([^/]+)\/?$/;

function parseHash(hash: string): HashRoute {
  const m = TICKER_RE.exec(hash);
  if (m) return { route: "ticker", symbol: decodeURIComponent(m[1]) };
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
