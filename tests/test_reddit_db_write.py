from sources.screeners.reddit_screener.db import (connect, ensure_schema, prune, upsert_tickers,
                                write_snapshot)


def _rows():
    return [
        {"ticker": "MU", "name": "Micron", "rank": 1, "mentions": 1147,
         "upvotes": 5135, "rank_24h_ago": 1, "mentions_24h_ago": 951},
        {"ticker": "BTC.X", "name": "Bitcoin", "rank": 2, "mentions": 100,
         "upvotes": 400, "rank_24h_ago": None, "mentions_24h_ago": None},
    ]


def test_write_snapshot_stores_rows_and_count():
    conn = connect(":memory:")
    ensure_schema(conn)
    sid, n = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", _rows())
    assert n == 2
    assert conn.execute(
        "SELECT ticker_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 2
    got = conn.execute(
        "SELECT mentions, upvotes FROM observations "
        "WHERE snapshot_id=? AND ticker='MU'", (sid,)).fetchone()
    assert got == (1147, 5135)


def test_write_snapshot_dedupes_duplicate_ticker():
    # ApeWisdom can repeat a symbol across pages; PK is (snapshot_id, ticker),
    # so a plain executemany would raise IntegrityError and abort the run.
    conn = connect(":memory:")
    ensure_schema(conn)
    dup = {"ticker": "MU", "name": "Micron", "rank": 1, "mentions": 1147,
           "upvotes": 5135, "rank_24h_ago": 1, "mentions_24h_ago": 951}
    sid, n = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks",
                            [dup, dict(dup)])
    assert n == 1  # collapsed to one row
    assert conn.execute(
        "SELECT COUNT(*) FROM observations WHERE snapshot_id=?",
        (sid,)).fetchone()[0] == 1
    assert conn.execute(
        "SELECT ticker_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 1


def test_upsert_tickers_classifies_and_tracks_seen():
    conn = connect(":memory:")
    ensure_schema(conn)
    upsert_tickers(conn, _rows(), "2026-07-01T00:00:00+00:00")
    upsert_tickers(conn, _rows(), "2026-07-02T00:00:00+00:00")  # second sighting
    mu = conn.execute(
        "SELECT asset_type, first_seen, last_seen FROM tickers "
        "WHERE ticker='MU'").fetchone()
    assert mu == ("stock", "2026-07-01T00:00:00+00:00", "2026-07-02T00:00:00+00:00")
    btc_type = conn.execute(
        "SELECT asset_type FROM tickers WHERE ticker='BTC.X'").fetchone()[0]
    assert btc_type == "crypto"


def test_v_signals_math_and_null_guards():
    conn = connect(":memory:")
    ensure_schema(conn)
    rows = [
        {"ticker": "MU", "name": "Micron", "rank": 1, "mentions": 1147,
         "upvotes": 5135, "rank_24h_ago": 3, "mentions_24h_ago": 951},
        # mentions_24h_ago = 0 -> pct_change must be NULL, not a divide error
        {"ticker": "NEW", "name": "New Co", "rank": 5, "mentions": 10,
         "upvotes": 20, "rank_24h_ago": None, "mentions_24h_ago": 0},
    ]
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", rows)
    mu = conn.execute(
        "SELECT mention_delta, rank_delta, upvote_ratio FROM v_signals "
        "WHERE ticker='MU'").fetchone()
    assert mu == (196, 2, 5135 / 1147)
    new_pct = conn.execute(
        "SELECT mention_pct_change FROM v_signals WHERE ticker='NEW'").fetchone()[0]
    assert new_pct is None


def test_prune_removes_old_snapshots():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-06-01T00:00:00+00:00", "all-stocks", _rows())
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", _rows())
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
