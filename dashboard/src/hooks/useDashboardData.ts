// Fetches the static export (`reports/data.json`, served at `./data.json`
// relative to the page) once on mount. Surfaces two distinct failure modes
// as `error`: the fetch itself failing (network/404), and a successful
// fetch of a top-level `{ error: "..." }` document (the exporter itself
// failed — see dashboard_lib/data.py's export_data() error path). `stale`
// flags a document whose `generated_at` is more than 36h behind the
// client's clock — the nightly job missed a run. The total-failure error
// document still carries `generated_at` (it's set from the literal dict in
// data.py's error path), so `generatedAt` surfaces it for App's
// generation-failed banner; a bare fetch failure never got a document at
// all, so it stays undefined there.

import { useEffect, useState } from "react";
import type { DashboardDoc } from "../types";

const STALE_MS = 36 * 60 * 60 * 1000;

export interface DashboardDataState {
  doc?: DashboardDoc;
  error?: string;
  generatedAt?: string;
  stale: boolean;
}

interface ErrorDoc {
  error: string;
  generated_at?: string;
}

function isStale(generatedAt: string): boolean {
  const generated = Date.parse(generatedAt);
  if (Number.isNaN(generated)) return false;
  return Date.now() - generated > STALE_MS;
}

export function useDashboardData(): DashboardDataState {
  const [state, setState] = useState<DashboardDataState>({ stale: false });

  useEffect(() => {
    let cancelled = false;

    fetch("./data.json")
      .then((res) => {
        if (!res.ok) throw new Error(`data.json fetch failed: ${res.status}`);
        return res.json() as Promise<DashboardDoc | ErrorDoc>;
      })
      .then((doc) => {
        if (cancelled) return;
        if ("error" in doc && doc.error) {
          setState({ error: doc.error, generatedAt: doc.generated_at, stale: false });
          return;
        }
        const full = doc as DashboardDoc;
        setState({ doc: full, stale: isStale(full.generated_at) });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState({
          error: err instanceof Error ? err.message : String(err),
          stale: false,
        });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
