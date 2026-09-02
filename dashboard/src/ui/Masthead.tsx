// The page header: publication name, edition date + snapshot number, and
// the theme toggle. (Deliberately no global ticker search box —
// per-ticker navigation happens through scorecard symbol links and the
// per-table filters.)

import type { ReactNode } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemeMode } from "../hooks/useTheme";
import { ToggleGroup, ToggleGroupItem } from "../components/ui/toggle-group";

export interface MastheadProps {
  editionDate: string;
  snapshotNumber: number | null;
  /** Slot before the title — AppShell puts the sidebar trigger here. */
  leading?: ReactNode;
}

const THEME_OPTIONS: { value: ThemeMode; icon: typeof Sun; label: string }[] = [
  { value: "system", icon: Monitor, label: "System theme" },
  { value: "light", icon: Sun, label: "Light theme" },
  { value: "dark", icon: Moon, label: "Dark theme" },
];

export function ThemeToggle() {
  const [mode, setMode] = useTheme();
  return (
    // Single-select ToggleGroup: Radix renders the items as radios, so the
    // current mode is the checked one. An empty value is the group's
    // deselect, which a theme has no meaning for — ignore it.
    <ToggleGroup
      type="single"
      variant="outline"
      size="sm"
      aria-label="Theme"
      value={mode}
      onValueChange={(value) => {
        if (value) setMode(value as ThemeMode);
      }}
    >
      {THEME_OPTIONS.map(({ value, icon: Icon, label }) => (
        <ToggleGroupItem key={value} value={value} aria-label={label}>
          <Icon />
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

export function Masthead({ editionDate, snapshotNumber, leading }: MastheadProps) {
  return (
    <header className="mast mb-5 flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b pb-4">
      <div className="flex items-start gap-2">
        {leading}
        <div>
        {/* h1, not p: the main page's only top-level heading — the strand and
            section h2s below need something to hang off for AT users. */}
        <h1 className="text-xl leading-tight font-semibold tracking-tight">
          Agentic Trading Research Bot
        </h1>
        <p className="text-muted-foreground m-0 text-sm">
          A nightly digest of research notes; nothing here is investment advice
        </p>
        </div>
      </div>
      {/* Below sm this row wraps under the title, so it spans the full
          width: the two-line edition block left-aligned at the left edge,
          toggle at the right. From sm up it hugs the right edge, text
          right-aligned. (One joined line was tried: "Snapshot #61" split
          across lines at 390px.) */}
      <div className="mast-meta flex w-full items-center justify-between gap-3 sm:w-auto sm:justify-end">
        <div className="text-muted-foreground text-left text-xs leading-relaxed sm:text-right">
          Edition <b className="text-foreground font-medium">{editionDate}</b>
          {snapshotNumber !== null && (
            <>
              <br />
              Snapshot <b className="text-foreground font-medium">#{snapshotNumber}</b>
            </>
          )}
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
