import pytest

from pipeline.leads import db

NOW = "2026-07-04T12:00:00+00:00"


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _lead(**over):
    lead = {"instrument": "GLD", "instrument_kind": "etf",
            "signal": "cot_commercial_extreme", "direction": "long",
            "signal_type": "mean_reversion",
            "implementation": "cross_sectional", "horizon_band": "weeks",
            "score": 95.0, "rank_pct": None, "as_of_date": "2026-06-23",
            "details": "{}"}
    lead.update(over)
    return lead


def test_write_and_finalize_snapshot_counts_leads():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW)
    db.write_leads(conn, sid, [_lead(), _lead(instrument="SPY")])
    assert db.finalize_snapshot(conn, sid) == 2
    row = conn.execute(
        "SELECT captured_at, lead_count, source FROM snapshots WHERE id=?",
        (sid,)).fetchone()
    assert row == (NOW, 2, "pipeline/leads")


def test_write_leads_rejects_unknown_vocab():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW)
    with pytest.raises(ValueError):
        db.write_leads(conn, sid, [_lead(signal_type="vibes")])
    with pytest.raises(ValueError):
        db.write_leads(conn, sid, [_lead(horizon_band="decades")])
    with pytest.raises(ValueError):
        db.write_leads(conn, sid, [_lead(direction="sideways")])
    with pytest.raises(ValueError):
        db.write_leads(conn, sid, [_lead(instrument_kind="option")])


def test_write_source_state_and_regime():
    conn = _fresh()
    sid = db.write_snapshot(conn, NOW)
    db.write_source_state(conn, sid, [
        {"source": "cftc", "db_path": "cftc.db",
         "source_captured_at": NOW, "max_data_date": "2026-06-23"}])
    db.write_regime(conn, sid, {
        "as_of_date": "2026-06-01", "cpi_yoy": 3.4, "unrate": 4.1,
        "yield_curve_inverted": 0, "hy_spread": 3.1, "late_cycle": 1,
        "exposure_scalar": 0.5, "regime_incomplete": 0})
    assert conn.execute("SELECT max_data_date FROM source_state "
                        "WHERE snapshot_id=?", (sid,)).fetchone() == ("2026-06-23",)
    assert conn.execute("SELECT exposure_scalar, late_cycle FROM regime "
                        "WHERE snapshot_id=?", (sid,)).fetchone() == (0.5, 1)


def test_prune_cascades_all_children():
    conn = _fresh()
    old = db.write_snapshot(conn, "2026-01-01T00:00:00+00:00")
    db.write_leads(conn, old, [_lead()])
    db.write_source_state(conn, old, [
        {"source": "cftc", "db_path": "cftc.db",
         "source_captured_at": NOW, "max_data_date": "2026-06-23"}])
    db.write_regime(conn, old, {
        "as_of_date": None, "cpi_yoy": None, "unrate": None,
        "yield_curve_inverted": None, "hy_spread": None, "late_cycle": 0,
        "exposure_scalar": 1.0, "regime_incomplete": 1})
    new = db.write_snapshot(conn, NOW)
    db.write_leads(conn, new, [_lead()])
    assert db.prune(conn, keep_days=30, now_iso=NOW) == 1
    for table in ("leads", "source_state", "regime"):
        assert conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE snapshot_id=?",
            (old,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM leads WHERE snapshot_id=?",
                        (new,)).fetchone()[0] == 1
