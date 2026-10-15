// Lets a section component re-state the verdict chip SectionShell renders
// in its header (the equity curve's range picker changes what "ahead of
// SPY" is measured over). The shell owns the state; a component sets an
// override or null to return to the exporter's verdict. Kept out of
// SectionShell.tsx so that file exports only components (fast refresh).

import { createContext, useContext } from "react";
import type { Verdict } from "../types";

export type SetVerdictOverride = (verdict: Verdict | null) => void;

export const SectionVerdictContext = createContext<SetVerdictOverride>(() => {});

export function useSetSectionVerdict(): SetVerdictOverride {
  return useContext(SectionVerdictContext);
}
