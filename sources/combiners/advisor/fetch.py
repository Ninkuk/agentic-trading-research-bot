"""Read-only extraction from composite (scorecard), portfolio (holdings),
stocks/etfs (ATR + close), and scorer (efficacy). No network anywhere in
this package. Every reader expects its source attached as `src`."""

import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


def read_composite_header(conn):
    """Latest composite snapshot (captured_at + regime); None when empty."""
    row = conn.execute(
        "SELECT s.id, s.captured_at, m.regime FROM src.snapshots s"
        " LEFT JOIN src.market_regime m ON m.snapshot_id = s.id"
        " ORDER BY s.captured_at DESC, s.id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"snapshot_id": row[0], "captured_at": row[1], "regime": row[2]}


def read_scorecard(conn) -> dict:
    """symbol -> latest composite score row. SQLite resolves an attached
    view's internals in the view's own schema, so src.v_latest_scorecard is
    safe even though advisor.db has its own `snapshots` table."""
    return {
        r[0]: {"score_sum": r[1], "bullish": r[2], "bearish": r[3], "total": r[4]}
        for r in conn.execute(
            "SELECT symbol, score_sum, bullish, bearish, total FROM src.v_latest_scorecard"
        )
    }


def read_flagged(conn) -> list:
    """Symbols composite currently flags. Reading src.v_flagged keeps the
    flag threshold on composite's side — the advisor never re-states it."""
    return [r[0] for r in conn.execute("SELECT symbol FROM src.v_flagged ORDER BY symbol")]


def read_flag_signals(conn) -> dict:
    """symbol -> contributing voting evidence as (signal_id, via_crosswalk)
    pairs (latest snapshot; score-0 rows are informational and excluded).
    Pairs, not bare ids: the scorer grades the direct and crosswalked
    splits separately, so citations must not collapse them."""
    out: dict = {}
    for sym, sig, via in conn.execute(
        "SELECT entity, signal_id, via_crosswalk FROM src.v_signal_detail"
        " WHERE grain = 'ticker' AND score != 0"
    ):
        out.setdefault(sym, set()).add((sig, via))
    return out


def read_account(conn):
    """Latest account scalars + that snapshot's captured_at; None when
    portfolio.db has no snapshot yet."""
    row = conn.execute(
        "SELECT a.equity, a.cash, a.buying_power, s.captured_at"
        " FROM src.v_latest_account a JOIN src.snapshots s ON s.id = a.snapshot_id"
    ).fetchone()
    if row is None:
        return None
    return {"equity": row[0], "cash": row[1], "buying_power": row[2], "captured_at": row[3]}


def read_positions(conn) -> list:
    return [
        {"symbol": r[0], "quantity": r[1], "market_value": r[2]}
        for r in conn.execute("SELECT symbol, quantity, market_value FROM src.v_latest_positions")
    ]


def read_metrics(conn, symbols) -> dict:
    """symbol -> {atr, close, price_date} from a price DB's v_latest.
    Column names are stockanalysis.com camelCase — keep them quoted."""
    syms = sorted(symbols)
    if not syms:
        return {}
    qmarks = ",".join("?" * len(syms))
    return {
        r[0]: {"atr": r[1], "close": r[2], "price_date": r[3]}
        for r in conn.execute(
            f'SELECT symbol, "atr", "close", "priceDate" FROM src.v_latest'
            f" WHERE symbol IN ({qmarks})",
            syms,
        )
    }


def read_reliable_signals(conn) -> set:
    """(signal_id, via_crosswalk) pairs with a reliable efficacy row at any
    horizon — annotation input for size_caps. reliable is the scorer's
    sample-size floor (n_bench >= 30), not proof the signal works."""
    return {
        (r[0], r[1])
        for r in conn.execute(
            "SELECT DISTINCT signal_id, via_crosswalk FROM src.v_signal_efficacy WHERE reliable = 1"
        )
    }
