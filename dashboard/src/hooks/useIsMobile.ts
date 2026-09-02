// shadcn's use-mobile hook, with the cutoff raised from md (768) to lg
// (1024): a portrait tablet beside a 16rem rail leaves ~512px for tables
// built for 72rem, so tablets in portrait get the Sheet too. Starts
// undefined→false so the first paint is the desktop rail.

import { useEffect, useState } from "react";

const MOBILE_BREAKPOINT = 1024;

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const onChange = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    mql.addEventListener("change", onChange);
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return !!isMobile;
}
