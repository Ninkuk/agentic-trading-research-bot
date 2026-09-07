// Which of `ids` is the reader looking at: the first element in DOM
// order whose box crosses the band just under the viewport top (the
// sticky chip row's height, and a little more so a card that has
// mostly scrolled off no longer counts). Null before the first
// observation and under jsdom, which has no IntersectionObserver.

import { useEffect, useState } from "react";

export function useScrollSpy(ids: string[]): string | null {
  const [current, setCurrent] = useState<string | null>(null);
  const idKey = ids.join(",");

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const ordered = idKey ? idKey.split(",") : [];
    const visible = new Set<string>();
    const observer = new IntersectionObserver(
      (records) => {
        for (const r of records) {
          if (r.isIntersecting) visible.add(r.target.id);
          else visible.delete(r.target.id);
        }
        setCurrent(ordered.find((id) => visible.has(id)) ?? null);
      },
      { rootMargin: "-56px 0px -60% 0px" },
    );
    for (const id of ordered) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [idKey]);

  return current;
}
