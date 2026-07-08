"""Read-only extraction from stocks/etfs (prices) and composite (scores).
No network anywhere in this package."""

from sources.common.dbattach import attach_ro, detach  # noqa: F401  (re-exported)


def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots —
    INSERT OR IGNORE downstream dedupes, and re-harvesting nightly
    self-heals ledger gaps within the source's retention window."""
    return conn.execute(
        'SELECT DISTINCT symbol, "priceDate", "close" FROM src.metrics'
        ' WHERE "priceDate" IS NOT NULL AND "close" IS NOT NULL'
    ).fetchall()


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
