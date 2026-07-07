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
