// Two page-level banners App.tsx reaches for:
//   - GenerationFailedBanner: replaces the whole page. Fires either when
//     `data.json` itself couldn't be fetched, or when it fetched fine but
//     is the exporter's own total-failure error document
//     ({schema_version, generated_at, error} — see dashboard_lib/data.py's
//     export_data() error path). `generatedAt` is only known in the second
//     case (a fetch failure never got a document at all), hence optional.
//   - StaleBanner: sits above an otherwise-normal page when `generated_at`
//     is more than 36h behind the client clock. Dismissable for the
//     session only (no persistence) — a stale run should keep nagging on
//     the next visit rather than being silenced forever by one dismiss.

import { dateShort } from "../format";

export interface GenerationFailedBannerProps {
  message: string;
  generatedAt?: string;
}

export function GenerationFailedBanner({ message, generatedAt }: GenerationFailedBannerProps) {
  return (
    <div className="page">
      <div
        className="border-destructive/30 bg-destructive/5 space-y-2 rounded-lg border px-5 py-4"
        role="alert"
      >
        <p className="m-0 font-medium">
          Tonight's dashboard couldn't be generated, so there's nothing new to read yet.
        </p>
        <p className="mono text-destructive m-0">
          {message}
          {generatedAt && ` (last attempt ${dateShort(generatedAt)})`}
        </p>
        <p className="text-muted-foreground m-0 text-sm">
          The nightly job will try again on its own this evening. To retry now, run the dashboard
          export job (deploy/launchd/dashboard.sh) and reload this page.
        </p>
      </div>
    </div>
  );
}

export interface StaleBannerProps {
  generatedAt: string;
  onDismiss: () => void;
}

export function StaleBanner({ generatedAt, onDismiss }: StaleBannerProps) {
  return (
    <div
      className="lab-banner mx-auto mt-4 flex max-w-(--page-width) items-baseline gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-700 dark:text-amber-400"
      role="status"
    >
      <span>
        This edition is stale — generated {dateShort(generatedAt)}, more than 36 hours ago.
      </span>
      <button
        type="button"
        className="cursor-pointer font-medium underline underline-offset-2 hover:opacity-80"
        onClick={onDismiss}
      >
        dismiss
      </button>
    </div>
  );
}
