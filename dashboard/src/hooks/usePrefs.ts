// localStorage-backed preference, namespaced under `atrb:` so this app never
// collides with anything else sharing the origin. JSON-serialized; falls
// back to state-only (no persistence) when storage throws — private/
// incognito browsing can make localStorage reads/writes throw rather than
// silently no-op, and a crashed page is worse than an unpersisted toggle.

import { useCallback, useState } from "react";

const PREFIX = "atrb:";

function readStorage<T>(key: string, initial: T): T {
  try {
    const raw = window.localStorage.getItem(PREFIX + key);
    if (raw === null) return initial;
    return JSON.parse(raw) as T;
  } catch {
    return initial;
  }
}

function writeStorage(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // quota exceeded / private mode — the in-memory state below still
    // updates, so the UI keeps working for this session.
  }
}

export function usePrefs<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => readStorage(key, initial));

  const set = useCallback(
    (v: T) => {
      setValue(v);
      writeStorage(key, v);
    },
    [key],
  );

  return [value, set];
}
