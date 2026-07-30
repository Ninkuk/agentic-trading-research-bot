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
      <p className="unavailable" role="alert">
        Dashboard generation failed: {message}
        {generatedAt && ` (last attempt ${dateShort(generatedAt)})`}
      </p>
    </div>
  );
}

export interface StaleBannerProps {
  generatedAt: string;
  onDismiss: () => void;
}

export function StaleBanner({ generatedAt, onDismiss }: StaleBannerProps) {
  return (
    <div className="lab-banner" role="status">
      This edition is stale — generated {dateShort(generatedAt)}, more than 36 hours ago.{" "}
      <button type="button" onClick={onDismiss}>
        dismiss
      </button>
    </div>
  );
}
