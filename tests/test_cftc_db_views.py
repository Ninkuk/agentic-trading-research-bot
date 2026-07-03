from cftc_screener import db


def _seed(conn, code, series, name="M", asset_class="metals"):
    """series: list of (report_date, noncomm_long, noncomm_short)."""
    db.upsert_markets(conn, [{"code": code, "name": name,
                              "asset_class": asset_class}],
                      "2026-07-03T00:00:00+00:00")
    rows = [{"code": code, "report_date": d,
             "noncomm_long": lo, "noncomm_short": sh, "open_interest": 1000}
            for (d, lo, sh) in series]
    db.write_cot(conn, code, rows)


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_net_computes_net_positions():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-23", 217028, 35689)])
    net = conn.execute(
        "SELECT net_noncomm FROM v_net WHERE code='G'").fetchone()[0]
    assert net == 217028 - 35689


def test_v_latest_picks_most_recent_week():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-09", 10, 0), ("2026-06-23", 50, 0),
                      ("2026-06-16", 20, 0)])
    row = conn.execute(
        "SELECT report_date, net_noncomm FROM v_latest WHERE code='G'").fetchone()
    assert row == ("2026-06-23", 50)


def test_cot_index_is_percentile_within_range():
    conn = _fresh()
    # net walks 0, 100, then 50 (latest). Window covers all 3: lo=0, hi=100.
    _seed(conn, "G", [("2026-06-09", 0, 0), ("2026-06-16", 100, 0),
                      ("2026-06-23", 50, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='G'").fetchone()[0]
    assert abs(idx - 50.0) < 1e-9


def test_cot_index_is_100_at_max():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='G'").fetchone()[0]
    assert idx == 100.0


def test_v_extremes_flags_crowded_market_only():
    conn = _fresh()
    _seed(conn, "HOT", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])   # index 100
    # net walks 0, 100, then 50 (latest) -> lo=0, hi=100 -> index 50 (mid-range)
    _seed(conn, "MILD", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0),
                         ("2026-06-30", 50, 0)])                          # index 50
    codes = {r[0] for r in conn.execute("SELECT code FROM v_extremes")}
    assert "HOT" in codes
    assert "MILD" not in codes


def test_cot_index_is_null_on_flat_window():
    conn = _fresh()
    # net stays 0 across both weeks -> lo == hi == 0 -> CASE WHEN hi<>lo guard
    # returns NULL (no divide-by-zero).
    _seed(conn, "FLAT", [("2026-06-16", 0, 0), ("2026-06-23", 0, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='FLAT'").fetchone()[0]
    assert idx is None


def test_v_extremes_flags_crowded_short():
    conn = _fresh()
    # net walks 100 then 0 (latest) -> lo=0, hi=100, latest=lo -> index 0.
    # Exercises the cot_index <= 10 branch of v_extremes.
    _seed(conn, "SHORT", [("2026-06-16", 100, 0), ("2026-06-23", 0, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='SHORT'").fetchone()[0]
    assert idx == 0.0
    codes = {r[0] for r in conn.execute("SELECT code FROM v_extremes")}
    assert "SHORT" in codes


def test_v_positioning_passthrough_columns():
    conn = _fresh()
    db.upsert_markets(conn, [{"code": "P", "name": "Pork",
                              "asset_class": "ags"}],
                      "2026-07-03T00:00:00+00:00")
    # Single week: net_noncomm = 100 - 0 = 100, and with a flat 1-row window
    # lo == hi == 100 -> cot_index is NULL. Seed a prior week so the window has
    # a range and cot_index resolves to a concrete value at the latest row.
    db.write_cot(conn, "P", [
        {"code": "P", "report_date": "2026-06-16",
         "noncomm_long": 0, "noncomm_short": 0, "open_interest": 900,
         "pct_oi_noncomm_long": 10.0, "chg_oi": 0},
        {"code": "P", "report_date": "2026-06-23",
         "noncomm_long": 100, "noncomm_short": 0, "open_interest": 1000,
         "pct_oi_noncomm_long": 42.5, "chg_oi": 100},
    ])
    row = conn.execute(
        "SELECT code, name, asset_class, report_date, open_interest, "
        "net_noncomm, cot_index, pct_oi_noncomm_long, chg_oi "
        "FROM v_positioning WHERE code='P'").fetchone()
    assert row == ("P", "Pork", "ags", "2026-06-23", 1000, 100, 100.0, 42.5, 100)
