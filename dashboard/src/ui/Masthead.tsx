// The page header: publication name, edition date + snapshot number, and
// the global ticker search box. The box uppercases as you type (tickers
// are conventionally upper-case, and it doubles as a hint this is a symbol
// field, not free text) and on Enter jumps straight to that ticker's
// drill-down route via the same `#/ticker/<SYMBOL>` convention useHashRoute
// parses — no router dependency needed for a single destination.

import { useState, type KeyboardEvent } from "react";

export interface MastheadProps {
  editionDate: string;
  snapshotNumber: number | null;
}

export function Masthead({ editionDate, snapshotNumber }: MastheadProps) {
  const [symbol, setSymbol] = useState("");

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>): void {
    if (e.key !== "Enter") return;
    const trimmed = symbol.trim();
    if (!trimmed) return;
    location.hash = `#/ticker/${trimmed}`;
  }

  return (
    <header className="mast">
      <div>
        <p className="name">
          Agentic Trading Research <em>Bot</em>
        </p>
        <p className="tag">Nightly signal digest — research notes, not investment advice</p>
      </div>
      <div className="edition">
        Edition <b>{editionDate}</b>
        <br />
        {snapshotNumber !== null && (
          <>
            Snapshot <b>#{snapshotNumber}</b>
            <br />
          </>
        )}
        <input
          type="text"
          className="ticker-search"
          placeholder="Ticker…"
          aria-label="Search ticker"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          onKeyDown={handleKeyDown}
        />
      </div>
    </header>
  );
}
