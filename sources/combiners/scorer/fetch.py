"""Read-only extraction from stocks/etfs (prices) and composite (scores).
No network anywhere in this package."""

from sources.combiners.composite import candidates
from sources.common.clock import phx_date
from sources.common.dbattach import attach_ro, detach  # noqa: F401  (re-exported)


def read_candidate_rows(conn):
    """(screen_date, screen_version, rows) from the ATTACHed stocks.db, via
    the candidates screen itself — one source of truth for what qualifies
    (its unqualified `v_latest` resolves to src because scorer.db has none;
    a test pins that). screen_date is the Phoenix date of src.snapshots'
    newest header, NEVER candidates.snapshot_date(conn): the scorer's own
    run headers share the `snapshots` table name and main wins resolution.
    Returns (None, version, []) when the header is unavailable."""
    row = conn.execute(
        "SELECT captured_at FROM src.snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if not row or not row[0]:
        return None, candidates.SCREEN_VERSION, []
    rows = [
        {
            "symbol": r["symbol"],
            "fcf_yield": r["fcfYield"],
            "rsi": r["rsi"],
            "high52ch": r["high52ch"],
            "fscore": r["fScore"],
            "roic": r["roic"],
            "roic5y": r["roic5y"],
            "rev_growth_3y": r["revenueGrowth3Y"],
            "net_debt_ebitda": r["netDebtEbitda"],
            "shares_yoy": r["sharesYoY"],
            "accruals_pct_assets": r["accrualsPctAssets"],
            "via_rsi": int(r["rsi"] is not None and 0 < r["rsi"] < candidates.RSI_MAX),
            "via_drawdown": int(
                r["high52ch"] is not None and r["high52ch"] <= candidates.HIGH52_DISLOCATION_MAX
            ),
        }
        for r in candidates.screen(conn)
    ]
    return phx_date(row[0]), candidates.SCREEN_VERSION, rows


def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots.

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
       (measured live: NVDA 201.01 vs a 204.12 close). Phoenix is UTC-7
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


def harvest_equity(conn) -> list:
    """(obs_date, equity, cash, captured_at) — one row per Phoenix date from
    the ATTACHed portfolio.db, ahead of its snapshot prune.

    Within a date the snapshot captured in the post-close window
    (13:00-16:59 Phoenix — the stable 14:30 daily slot) beats any
    out-of-window one: the broker's overnight reads land ~21:20 Phoenix and
    return glitch equity ($0.00 / $10.80 with cash unchanged, observed
    2026-07). Ties and window-less dates fall back to latest captured_at.
    Re-harvest is idempotent repair (upsert_equity is last-write-wins).

    Zero equity is EXCLUDED outright, whichever window it sits in — the
    glitch also occurs in-window (2026-07-13/14/16/17 each have a single
    14:30 Phoenix snapshot reading $0.00 with cash intact), and a zero in the
    permanent ledger makes the leg into it exactly -100%: the chained product
    pins at 0 forever and the leg out divides by zero into NULL, so inception
    would print -100.00% permanently. Excluded dates simply become ordinary
    ledger gaps, which only widen the neighbouring leg.

    LIMITATION: the fallback is value-blind, so a nonzero glitch on a date
    with ONLY out-of-window snapshots (live 2026-07-07 $16.21, 2026-07-08
    $10.80) still lands in the ledger, and a window ANCHOR on one prints
    absurd TWR. Repair is manual — correct the source and re-harvest
    (last-write-wins), or fix the ledger row directly."""
    cols = {r[1] for r in conn.execute("PRAGMA src.table_info(account)")}
    missing = {"snapshot_id", "equity", "cash"} - cols
    if missing:
        raise ValueError("portfolio account table missing columns")
    return conn.execute(
        "SELECT obs_date, equity, cash, captured_at FROM ("
        " SELECT substr(datetime(s.captured_at, '-7 hours'), 1, 10) AS obs_date,"
        "        a.equity, a.cash, s.captured_at,"
        "        ROW_NUMBER() OVER ("
        "            PARTITION BY substr(datetime(s.captured_at, '-7 hours'), 1, 10)"
        "            ORDER BY (CAST(substr(datetime(s.captured_at, '-7 hours'), 12, 2)"
        "                      AS INTEGER) BETWEEN 13 AND 16) DESC,"
        "                     s.captured_at DESC"
        "        ) AS rn"
        " FROM src.snapshots s JOIN src.account a ON a.snapshot_id = s.id"
        " WHERE a.equity IS NOT NULL AND a.equity > 0"
        ") WHERE rn = 1 ORDER BY obs_date"
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
        dict(
            symbol=r[0],
            score_sum=r[1],
            total=r[2],
            bullish=r[3],
            bearish=r[4],
            in_portfolio=r[5],
        )
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
