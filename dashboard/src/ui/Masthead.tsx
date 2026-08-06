// The page header: publication name, edition date + snapshot number, and
// the theme toggle. (The global ticker search box was removed 2026-07-30 —
// per-ticker navigation happens through scorecard symbol links and the
// per-table filters.)

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemeMode } from "../hooks/useTheme";
import { Button } from "../components/ui/button";

export interface MastheadProps {
  editionDate: string;
  snapshotNumber: number | null;
}

const THEME_OPTIONS: { value: ThemeMode; icon: typeof Sun; label: string }[] = [
  { value: "system", icon: Monitor, label: "System theme" },
  { value: "light", icon: Sun, label: "Light theme" },
  { value: "dark", icon: Moon, label: "Dark theme" },
];

export function ThemeToggle() {
  const [mode, setMode] = useTheme();
  return (
    <div className="bg-muted flex items-center gap-0.5 rounded-lg p-0.5">
      {THEME_OPTIONS.map(({ value, icon: Icon, label }) => (
        <Button
          key={value}
          type="button"
          variant={mode === value ? "outline" : "ghost"}
          size="icon"
          className="size-7"
          aria-label={label}
          aria-pressed={mode === value}
          onClick={() => setMode(value)}
        >
          <Icon className="size-3.5" />
        </Button>
      ))}
    </div>
  );
}

export function Masthead({ editionDate, snapshotNumber }: MastheadProps) {
  return (
    <header className="mast mb-5 flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b pb-4">
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
      <div className="flex items-center gap-3">
        <div className="text-muted-foreground text-right text-xs leading-relaxed">
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
