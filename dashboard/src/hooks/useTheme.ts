// System-default light/dark with a manual override, persisted in
// localStorage. Applies/removes `.dark` on <html> and keeps
// `color-scheme` in sync so native UI (scrollbars, form controls) follows.

import { useEffect, useState } from "react";

export type ThemeMode = "system" | "light" | "dark";

const STORAGE_KEY = "theme";

export function useTheme(): [ThemeMode, (m: ThemeMode) => void] {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "light" || saved === "dark" ? saved : "system";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
    // jsdom has no matchMedia — treat "system" as light there.
    const media =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;
    function apply(): void {
      const dark = mode === "dark" || (mode === "system" && (media?.matches ?? false));
      document.documentElement.classList.toggle("dark", dark);
      document.documentElement.style.colorScheme = dark ? "dark" : "light";
    }
    apply();
    media?.addEventListener("change", apply);
    return () => media?.removeEventListener("change", apply);
  }, [mode]);

  return [mode, setMode];
}
