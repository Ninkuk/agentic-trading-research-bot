// The app shell: fetch state -> route switch.
//
// - Nothing loaded yet, no error either: a plain loading state.
// - `doc` never arrived (fetch itself failed, or the exporter wrote its own
//   total-failure error document): a full-page GenerationFailedBanner,
//   with `generated_at` shown when the error document carried one.
// - `doc` loaded but stale (generated_at > 36h old): the normal page, with
//   a dismissable-for-this-session (never persisted) banner above it — a
//   stale run should keep nagging on the next visit.
// - Route switch via useHashRoute: `#/` (or anything else) renders Main;
//   `#/ticker/<SYMBOL>` renders a stub Task 15 replaces with the real
//   drill-down.

import { useState } from "react";
import { useDashboardData } from "./hooks/useDashboardData";
import { useHashRoute } from "./hooks/useHashRoute";
import { Main } from "./routes/Main";
import { GenerationFailedBanner, StaleBanner } from "./ui/Banners";

function TickerPlaceholder({ symbol }: { symbol: string }) {
  return (
    <div className="page">
      <p className="empty">Ticker detail for {symbol} — coming soon.</p>
    </div>
  );
}

function App() {
  const { doc, error, generatedAt, stale } = useDashboardData();
  const route = useHashRoute();
  const [staleDismissed, setStaleDismissed] = useState(false);

  if (!doc && !error) {
    return (
      <div className="page">
        <p className="empty">Loading tonight's edition…</p>
      </div>
    );
  }

  if (!doc) {
    return <GenerationFailedBanner message={error ?? "unknown error"} generatedAt={generatedAt} />;
  }

  return (
    <>
      {stale && !staleDismissed && (
        <StaleBanner generatedAt={doc.generated_at} onDismiss={() => setStaleDismissed(true)} />
      )}
      {route.route === "ticker" ? <TickerPlaceholder symbol={route.symbol} /> : <Main doc={doc} />}
    </>
  );
}

export default App;
