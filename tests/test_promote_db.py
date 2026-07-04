from pipeline.promote import db

NOW = "2026-07-04T21:00:00+00:00"


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _candidate(**over):
    row = {"instrument": "GLD", "instrument_kind": "etf", "direction": "long",
           "det_score": 0.95, "horizon_band": "weeks",
           "signals": '[{"signal":"cot_commercial_extreme","det_score":0.95}]',
           "price": 200.0, "atr": 4.0, "sector": "metals",
           "next_earnings_date": None, "shares": 100, "stop_price": 192.0,
           "stop_distance": 8.0, "risk_dollars": 1000.0,
           "realized_risk": 800.0, "size_lo": 0, "size_hi": 100,
           "as_of_date": "2026-07-01", "details": "[]"}
    row.update(over)
    return row


def test_schema_views_and_idempotence():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"snapshots", "candidates", "rejections", "v_latest_candidates",
            "v_rejection_summary", "v_gate_input"} <= names
    db.ensure_schema(conn)


def test_snapshot_lifecycle_and_counts():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW, equity=100000.0, regime_scalar=0.5,
                            leads_snapshot_id=7, config_hash="c" * 64)
    db.write_candidates(conn, sid, [_candidate()])
    db.write_rejections(conn, sid, [
        {"instrument": "PENNY", "direction": "long", "gate": "liquidity",
         "reason": "price 3.10 < 5.0"},
        {"instrument": "XYZ", "direction": "short", "gate": "direction",
         "reason": "allow_short=False"}])
    assert db.finalize_snapshot(conn, sid) == (1, 2)
    row = conn.execute("SELECT equity, regime_scalar, leads_snapshot_id, "
                       "config_hash FROM snapshots WHERE id=?", (sid,)).fetchone()
    assert row == (100000.0, 0.5, 7, "c" * 64)


def test_v_latest_candidates_scopes_to_newest_snapshot():
    conn = _fresh()
    old = db.write_snapshot(conn, "2026-07-01T00:00:00+00:00", 1.0, 1.0, 1, "a" * 64)
    db.write_candidates(conn, old, [_candidate(instrument="OLD")])
    new = db.write_snapshot(conn, NOW, 1.0, 1.0, 2, "a" * 64)
    db.write_candidates(conn, new, [_candidate()])
    rows = [r[0] for r in conn.execute(
        "SELECT instrument FROM v_latest_candidates")]
    assert rows == ["GLD"]


def test_v_rejection_summary_counts_per_gate():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW, 1.0, 1.0, 1, "a" * 64)
    db.write_rejections(conn, sid, [
        {"instrument": "A", "direction": "long", "gate": "liquidity",
         "reason": "x"},
        {"instrument": "B", "direction": "long", "gate": "liquidity",
         "reason": "y"},
        {"instrument": "C", "direction": "short", "gate": "direction",
         "reason": "z"}])
    rows = dict(conn.execute(
        "SELECT gate, n FROM v_rejection_summary").fetchall())
    assert rows == {"liquidity": 2, "direction": 1}


def test_v_gate_input_carries_snapshot_context():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW, 50000.0, 0.5, 3, "b" * 64)
    db.write_candidates(conn, sid, [_candidate()])
    row = conn.execute(
        "SELECT instrument, shares, size_lo, size_hi, equity, regime_scalar "
        "FROM v_gate_input").fetchone()
    assert row == ("GLD", 100, 0, 100, 50000.0, 0.5)


def test_prune_cascades_both_children():
    conn = _fresh()
    old = db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1.0, 1.0, 1, "a" * 64)
    db.write_candidates(conn, old, [_candidate()])
    db.write_rejections(conn, old, [
        {"instrument": "A", "direction": "long", "gate": "liquidity",
         "reason": "x"}])
    db.write_snapshot(conn, NOW, 1.0, 1.0, 2, "a" * 64)
    assert db.prune(conn, keep_days=30, now_iso=NOW) == 1
    assert conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM rejections").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
