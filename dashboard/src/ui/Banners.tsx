// Two page-level banners App.tsx reaches for, both on the shadcn Alert:
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
//     role="status", not Alert's default "alert": stale is a notice, not
//     an interruption.

import { CircleAlert, TriangleAlert } from "lucide-react";
import { dateShort } from "../format";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Button } from "../components/ui/button";

export interface GenerationFailedBannerProps {
  message: string;
  generatedAt?: string;
}

export function GenerationFailedBanner({ message, generatedAt }: GenerationFailedBannerProps) {
  return (
    <div className="page">
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>Tonight's dashboard couldn't be generated</AlertTitle>
        <AlertDescription>
          <p className="m-0 font-mono">
            {message}
            {generatedAt && ` (last attempt ${dateShort(generatedAt)})`}
          </p>
          <p className="m-0">
            There's nothing new to read yet. The nightly job will try again on its own this
            evening; to retry now, run the dashboard export job (deploy/launchd/dashboard.sh) and
            reload this page.
          </p>
        </AlertDescription>
      </Alert>
    </div>
  );
}

export interface StaleBannerProps {
  generatedAt: string;
  onDismiss: () => void;
}

export function StaleBanner({ generatedAt, onDismiss }: StaleBannerProps) {
  return (
    <Alert
      variant="warning"
      role="status"
      className="lab-banner mx-auto mt-4 max-w-(--page-width)"
    >
      <TriangleAlert />
      <AlertDescription className="flex flex-wrap items-baseline gap-x-2">
        <span>
          This edition is stale — generated {dateShort(generatedAt)}, more than 36 hours ago.
        </span>
        <Button variant="link" size="sm" className="h-auto p-0" onClick={onDismiss}>
          dismiss
        </Button>
      </AlertDescription>
    </Alert>
  );
}
