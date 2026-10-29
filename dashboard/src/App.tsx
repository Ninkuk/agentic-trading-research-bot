// The app shell: fetch state -> route switch.
//
// - Nothing loaded yet, no error either: a plain loading state.
// - `doc` never arrived (fetch itself failed, or the exporter wrote its own
//   total-failure error document): a full-page GenerationFailedBanner,
//   with `generated_at` shown when the error document carried one.
// - `doc` loaded but stale (generated_at > 36h old): the normal page, with
//   a dismissable-for-this-session (never persisted) banner above it — a
//   stale run should keep nagging on the next visit.
// - Route switch via useHashRoute: `#/` renders Home, the visitor-facing
//   front door, outside the sidebar shell (it carries its own top bar);
//   inside AppShell, `#/ticker/<SYMBOL>` renders the per-ticker drill-down
//   (TickerDetail) and everything else renders Main, which picks the strand.

import { useState } from "react";
import { useDashboardData } from "./hooks/useDashboardData";
import { useHashRoute } from "./hooks/useHashRoute";
import { Home } from "./routes/Home";
import { Main } from "./routes/Main";
import { TickerDetail } from "./routes/TickerDetail";
import { AppShell } from "./ui/AppShell";
import { GenerationFailedBanner, StaleBanner } from "./ui/Banners";
import { EmptyNote } from "./ui/EmptyNote";

function App() {
  const { doc, error, generatedAt, stale } = useDashboardData();
  const route = useHashRoute();
  const [staleDismissed, setStaleDismissed] = useState(false);

  if (!doc && !error) {
    return (
      <div className="page">
        <EmptyNote loading>Loading tonight's edition…</EmptyNote>
      </div>
    );
  }

  if (!doc) {
    return <GenerationFailedBanner message={error ?? "unknown error"} generatedAt={generatedAt} />;
  }

  const banner = stale && !staleDismissed && (
    <StaleBanner generatedAt={doc.generated_at} onDismiss={() => setStaleDismissed(true)} />
  );

  if (route.route === "main") {
    return (
      <>
        {banner}
        <Home doc={doc} />
      </>
    );
  }

  return (
    <AppShell doc={doc} route={route}>
      {banner}
      {route.route === "ticker" ? <TickerDetail doc={doc} symbol={route.symbol} /> : <Main doc={doc} />}
    </AppShell>
  );
}

export default App;
