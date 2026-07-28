from sources.combiners.advisor import db


def test_schema_idempotent(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # re-running must not error (views DROP+CREATE)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "position_heat", "size_caps"} <= tables
    views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {
        "v_latest_snapshot",
        "v_latest_heat",
        "v_book_heat",
        "v_group_heat",
        "v_disagreements",
        "v_latest_caps",
    } <= views


def test_wal_mode(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_strong_thresholds_pinned_to_composite_flag_view():
    # v_disagreements' `strong` must drift together with composite v_flagged
    # (same pin trick as scorer's FLAG_MIN_* constants).
    from sources.combiners.composite.db import _SCHEMA

    assert f"ABS(score_sum) >= {db.STRONG_MIN_ABS_SCORE}" in _SCHEMA
    assert f"total >= {db.STRONG_MIN_TOTAL}" in _SCHEMA


def test_prune_cascades_children(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (id, captured_at) VALUES (1, '2026-01-01T00:00:00+00:00')")
    conn.execute("INSERT INTO snapshots (id, captured_at) VALUES (2, '2026-07-07T00:00:00+00:00')")
    conn.execute(
        "INSERT INTO position_heat (snapshot_id, symbol, quantity) VALUES (1, 'AAPL', 1.0)"
    )
    conn.execute("INSERT INTO size_caps (snapshot_id, symbol) VALUES (1, 'NVDA')")
    conn.commit()
    assert db.prune(conn, keep_days=30, now_iso="2026-07-07T21:12:00+00:00") == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_heat").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM size_caps").fetchone()[0] == 0


# --- exit advice schema + migration (plan 003) ------------------------------


def test_exit_advice_table_has_expected_columns(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(exit_advice)")}
    assert cols == {
        "snapshot_id",
        "symbol",
        "quantity",
        "price",
        "avg_cost",
        "atr",
        "atr_stale",
        "score_sum",
        "total",
        "strong",
        "stop_price",
        "stop_distance_pct",
        "unrealized_pct",
        "trim_shares",
    }


def test_ensure_schema_adds_avg_cost_to_a_pre_existing_position_heat(tmp_path):
    """CREATE TABLE IF NOT EXISTS never widens an existing table. advisor.db
    exists on disk with live rows, so the ALTER path is the real one."""
    path = str(tmp_path / "advisor.db")
    conn = db.connect(path)
    # old shape: position_heat without avg_cost
    conn.executescript(
        "CREATE TABLE snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,"
        " equity REAL, cash REAL, buying_power REAL, portfolio_captured_at TEXT,"
        " composite_captured_at TEXT, regime TEXT, sources_failed INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE position_heat (snapshot_id INTEGER NOT NULL, symbol TEXT NOT NULL,"
        " group_name TEXT, quantity REAL NOT NULL, market_value REAL, atr REAL, price REAL,"
        " price_date TEXT, heat_dollars REAL, heat_pct REAL, weight_pct REAL, score_sum INTEGER,"
        " bullish INTEGER, bearish INTEGER, total INTEGER, atr_stale INTEGER,"
        " PRIMARY KEY (snapshot_id, symbol));"
    )
    conn.commit()
    assert "avg_cost" not in {r[1] for r in conn.execute("PRAGMA table_info(position_heat)")}

    db.ensure_schema(conn)
    assert "avg_cost" in {r[1] for r in conn.execute("PRAGMA table_info(position_heat)")}

    db.ensure_schema(conn)  # idempotent: a second run must not raise
    assert "avg_cost" in {r[1] for r in conn.execute("PRAGMA table_info(position_heat)")}


def test_ensure_schema_adds_research_verdict_to_a_pre_existing_size_caps(tmp_path):
    """Same trap as avg_cost: the live advisor.db's size_caps predates
    research_verdict, and CREATE TABLE IF NOT EXISTS never widens it. The
    write path must work against the migrated table, not just a fresh one
    (2026-07-27 outage: write_size_caps died on the missing column)."""
    path = str(tmp_path / "advisor.db")
    conn = db.connect(path)
    # old shape: size_caps as it existed on disk before 98156ed
    conn.executescript(
        "CREATE TABLE snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,"
        " equity REAL, cash REAL, buying_power REAL, portfolio_captured_at TEXT,"
        " composite_captured_at TEXT, regime TEXT, sources_failed INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE size_caps (snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),"
        " symbol TEXT NOT NULL, direction TEXT CHECK (direction IN ('bullish', 'bearish')),"
        " score_sum INTEGER, atr REAL, price REAL, cap_shares REAL, cap_dollars REAL,"
        " group_name TEXT, group_heat_pct REAL, reliable_signals INTEGER, total_signals INTEGER,"
        " exceeds_buying_power INTEGER NOT NULL DEFAULT 0,"
        " already_held INTEGER NOT NULL DEFAULT 0,"
        " PRIMARY KEY (snapshot_id, symbol));"
    )
    conn.commit()
    assert "research_verdict" not in {r[1] for r in conn.execute("PRAGMA table_info(size_caps)")}

    db.ensure_schema(conn)
    assert "research_verdict" in {r[1] for r in conn.execute("PRAGMA table_info(size_caps)")}

    db.ensure_schema(conn)  # idempotent: a second run must not raise
    assert "research_verdict" in {r[1] for r in conn.execute("PRAGMA table_info(size_caps)")}

    # the statement that failed in production must now succeed on the old DB
    sid = db.write_snapshot(conn, "2026-07-28T04:12:00+00:00")
    cap = dict(
        symbol="BBAI",
        direction="bullish",
        score_sum=3,
        atr=0.5,
        price=3.0,
        cap_shares=9.99,
        cap_dollars=30.0,
        group_name=None,
        group_heat_pct=None,
        reliable_signals=2,
        total_signals=2,
        exceeds_buying_power=0,
        already_held=0,
        research_verdict="pass",
    )
    db.write_size_caps(conn, sid, [cap])
    got = conn.execute("SELECT research_verdict FROM size_caps WHERE symbol='BBAI'").fetchone()
    assert got[0] == "pass"


def test_prune_cascades_exit_advice(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    old = db.write_snapshot(conn, "2025-01-01T00:00:00+00:00")
    conn.execute(
        "INSERT INTO exit_advice (snapshot_id, symbol, quantity) VALUES (?, 'AAPL', 1.0)", (old,)
    )
    conn.commit()
    db.prune(conn, keep_days=30, now_iso="2026-07-08T04:12:00+00:00")
    assert conn.execute("SELECT COUNT(*) FROM exit_advice").fetchone()[0] == 0, "orphaned rows"
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_option_heat_table_and_prune(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "option_heat" in names
    old = db.write_snapshot(conn, "2026-06-01T04:12:00+00:00")
    keep = db.write_snapshot(conn, "2026-07-08T04:12:00+00:00")
    for sid in (old, keep):
        conn.execute(
            "INSERT INTO option_heat (snapshot_id, occ_symbol, underlying, quantity)"
            " VALUES (?, 'XLE260821P00095000', 'XLE', 1.0)",
            (sid,),
        )
    conn.commit()
    db.prune(conn, keep_days=7, now_iso="2026-07-08T04:12:00+00:00")
    assert {r[0] for r in conn.execute("SELECT snapshot_id FROM option_heat")} == {keep}
