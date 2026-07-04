from pipeline.leads import db


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


def test_v_latest_leads_scopes_to_newest_snapshot_with_regime():
    conn = _fresh()
    old = db.write_snapshot(conn, "2026-07-01T00:00:00+00:00")
    db.write_leads(conn, old, [_lead(instrument="OLD")])
    new = db.write_snapshot(conn, "2026-07-04T00:00:00+00:00")
    db.write_leads(conn, new, [_lead()])
    db.write_regime(conn, new, {
        "as_of_date": "2026-06-01", "cpi_yoy": 3.4, "unrate": 4.1,
        "yield_curve_inverted": 1, "hy_spread": None, "late_cycle": 1,
        "exposure_scalar": 0.5, "regime_incomplete": 0})
    rows = conn.execute(
        "SELECT instrument, exposure_scalar FROM v_latest_leads").fetchall()
    assert rows == [("GLD", 0.5)]


def test_v_latest_leads_null_scalar_when_regime_leg_skipped():
    conn = _fresh()
    sid = db.write_snapshot(conn, "2026-07-04T00:00:00+00:00")
    db.write_leads(conn, sid, [_lead()])
    rows = conn.execute(
        "SELECT instrument, exposure_scalar FROM v_latest_leads").fetchall()
    assert rows == [("GLD", None)]


def test_v_leads_by_instrument_groups_for_confluence():
    conn = _fresh()
    sid = db.write_snapshot(conn, "2026-07-04T00:00:00+00:00")
    db.write_leads(conn, sid, [
        _lead(instrument="AAA", instrument_kind="stock",
              signal="quality_composite", signal_type="quality",
              horizon_band="months", direction="long"),
        _lead(instrument="AAA", instrument_kind="stock",
              signal="cot_commercial_extreme", direction="short"),
        _lead(instrument="GLD")])
    row = conn.execute(
        "SELECT signal_count, long_count, short_count, signals "
        "FROM v_leads_by_instrument WHERE instrument='AAA'").fetchone()
    assert row[0] == 2
    assert row[1] == 1
    assert row[2] == 1
    assert set(row[3].split(",")) == {"quality_composite",
                                      "cot_commercial_extreme"}
