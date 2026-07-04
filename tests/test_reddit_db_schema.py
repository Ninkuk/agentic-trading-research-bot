from sources.screeners.reddit_screener.db import connect, ensure_schema


def objects(conn, kind):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type=?", (kind,)).fetchall()}


def test_ensure_schema_creates_tables_and_views():
    conn = connect(":memory:")
    ensure_schema(conn)
    assert {"snapshots", "observations", "tickers"} <= objects(conn, "table")
    assert {"v_latest", "v_signals", "v_trending", "v_history"} <= objects(conn, "view")


def test_ensure_schema_is_idempotent():
    conn = connect(":memory:")
    ensure_schema(conn)
    ensure_schema(conn)  # second run must not raise
    assert {"snapshots", "observations", "tickers"} <= objects(conn, "table")


def test_observations_columns():
    conn = connect(":memory:")
    ensure_schema(conn)
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(observations)").fetchall()}
    assert cols == {"snapshot_id", "ticker", "name", "rank", "mentions",
                    "upvotes", "rank_24h_ago", "mentions_24h_ago"}
