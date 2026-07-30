// Container width via ResizeObserver with an explicit fallback — the
// chart-sizing companion to ChartContainer's responsive={false} escape
// hatch (Recharts' ResponsiveContainer measures 0x0 in jsdom, blanking
// every geometry assertion in tests; the fallback keeps them real).

import { useEffect, useRef, useState } from "react";

export function useMeasuredWidth(fallback: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const apply = () => {
      if (el.clientWidth > 0) setWidth(el.clientWidth);
    };
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    apply();
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}
