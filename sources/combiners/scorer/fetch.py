"""Read-only extraction from stocks/etfs (prices) and composite (scores).
No network anywhere in this package."""

from sources.common.dbattach import attach_ro, detach  # noqa: F401  (re-exported)


def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots.

    Two rules, both learned the hard way (see plans/000-*.md):

    1) Read "price", NOT "close". stockanalysis names these from a live-quote
       perspective: `price` is the last close for `priceDate`, while `close` is
       the PREVIOUS session's close. Harvesting "close" stamped every close with
       the NEXT trading day's date, handing entry_for() the composite date's own
       close — the exact overnight look-ahead that function exists to prevent.

    2) Only harvest a priceDate once it has SETTLED, i.e. from a snapshot taken
       on a LATER Phoenix calendar day. `close` was always settled by
       construction (it names a finished session), which is why rule 1's bug
       hid: switching to `price` exposes same-day, mid-session reads. A snapshot
       captured the evening of D reports an unsettled `price` for priceDate=D
       (measured 2026-07-08: NVDA 201.01 vs a 204.12 close). Phoenix is UTC-7
       year-round, so the shift is a bare '-7 hours' (cf. read_snapshots).

    MIN(s.id) makes the pick deterministic when several settled snapshots carry
    the same priceDate. They do NOT always agree — 186 such pairs in stocks.db
    disagree, nearly all sub-$5 names restated across a split (INLF 2026-07-02
    spans 0.0216..4.32). MIN picks the earliest settled report, i.e. the close
    as first published, which is the point-in-time value an opinion could have
    acted on; a later restatement is a basis change and belongs to
    v_basis_breaks, not to a silent overwrite. Without the aggregate,
    INSERT OR IGNORE would freeze whichever row the scan happened to yield
    first — deterministic only by accident."""
    # SQLite resolves an unknown double-quoted identifier to a STRING LITERAL,
    # so a metrics table without a `price` column would quietly harvest the
    # text 'price' into the permanent ledger. Fail the source instead: run()
    # catches this per-DB and skips it loudly.
    cols = {r[1] for r in conn.execute("PRAGMA src.table_info(metrics)")}
    missing = {"symbol", "priceDate", "price"} - cols
    if missing:
        raise ValueError(f"src.metrics missing column(s): {', '.join(sorted(missing))}")
    return [
        (r[0], r[1], r[2])
        for r in conn.execute(
            'SELECT m.symbol, m."priceDate", m."price", MIN(s.id)'
            " FROM src.metrics m JOIN src.snapshots s ON s.id = m.snapshot_id"
            ' WHERE m."priceDate" IS NOT NULL AND m."price" IS NOT NULL'
            "   AND substr(datetime(s.captured_at, '-7 hours'), 1, 10) > m.\"priceDate\""
            ' GROUP BY m.symbol, m."priceDate"'
        )
    ]


def read_snapshots(conn) -> list:
    """Composite snapshots that state an opinion (have a regime row).

    composite_date is derived by shifting captured_at (stored UTC) back 7
    hours before truncating to a date — Phoenix is UTC-7 fixed year-round,
    no DST — so the nightly run (e.g. 9:05pm Phoenix = 04:05Z next day)
    lands on the trading evening the opinion was actually formed on, not
    the UTC calendar day. Registration then waits for the first ledger
    close AFTER that date (next-day entry, no look-ahead), so a backlog
    snapshot registering after an outage still enters at its historically
    exact close as long as the price ledger retains it.
    """
    return [
        (r[0], r[1])
        for r in conn.execute(
            "SELECT s.id, substr(datetime(s.captured_at, '-7 hours'), 1, 10)"
            " FROM src.snapshots s"
            " JOIN src.market_regime m ON m.snapshot_id = s.id"
            " ORDER BY s.id"
        )
    ]


def read_ticker_scores(conn, csid) -> list:
    return [
        dict(symbol=r[0], score_sum=r[1], total=r[2], bullish=r[3], bearish=r[4], in_portfolio=r[5])
        for r in conn.execute(
            "SELECT symbol, score_sum, total, bullish, bearish,"
            " in_portfolio FROM src.ticker_scores"
            " WHERE snapshot_id = ?",
            (csid,),
        )
    ]


def read_signal_rows(conn, csid) -> list:
    """Ticker-grain, direction-bearing rows only (score 0 has no direction
    to grade — portfolio_holding / edgar_insider are informational)."""
    return [
        dict(signal_id=r[0], entity=r[1], score=r[2], via_crosswalk=r[3])
        for r in conn.execute(
            "SELECT signal_id, entity, score, via_crosswalk"
            " FROM src.signal_values WHERE snapshot_id = ?"
            " AND grain = 'ticker' AND score != 0",
            (csid,),
        )
    ]


def read_regime(conn, csid):
    row = conn.execute(
        "SELECT regime FROM src.market_regime WHERE snapshot_id = ?", (csid,)
    ).fetchone()
    return row[0] if row else None
