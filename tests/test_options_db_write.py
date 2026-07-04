from sources.screeners.cboe_options import db

FA = "2026-07-03T00:00:00+00:00"


def _rows(underlying="AAPL"):
    return [
        {"occ_symbol": f"{underlying}260717C00210000", "underlying": underlying,
         "expiration": "2026-07-17", "strike": 210.0, "type": "call",
         "bid": 1.0, "ask": 1.2, "mark": 1.1, "last": 1.1, "theo": 1.1,
         "iv": 0.3, "delta": 0.5, "gamma": 0.01, "theta": -0.1, "vega": 0.2,
         "rho": 0.05, "open_interest": 100, "volume": 250,
         "underlying_price": 308.45, "vol_oi_ratio": 2.5},
    ]


def _daily(underlying="AAPL"):
    return {"underlying": underlying, "underlying_price": 308.45, "close": 308.6,
            "iv30": 27.8, "total_call_volume": 250, "total_put_volume": 100,
            "put_call_volume_ratio": 0.4, "total_call_oi": 100,
            "total_put_oi": 80, "put_call_oi_ratio": 0.8}


def _seed(conn, underlying="AAPL"):
    db.upsert_underlying(conn, underlying, False, "2026-07-02")


def test_upsert_underlying_extends_first_last_seen():
    conn = db.connect(":memory:"); db.ensure_schema(conn)
    db.upsert_underlying(conn, "AAPL", False, "2026-07-02")
    db.upsert_underlying(conn, "AAPL", False, "2026-07-01")
    db.upsert_underlying(conn, "AAPL", False, "2026-07-03")
    row = conn.execute(
        "SELECT first_seen, last_seen, is_index FROM underlyings").fetchone()
    assert row == ("2026-07-01", "2026-07-03", 0)


def test_replace_day_overwrites_in_place():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    assert db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA) == 1
    # rerun with a shrunk set (empty) leaves no orphan for that day+underlying
    assert db.replace_day(conn, "2026-07-02", "AAPL", [], FA) == 0
    n = conn.execute(
        "SELECT COUNT(*) FROM option_snapshots WHERE snapshot_date='2026-07-02'"
    ).fetchone()[0]
    assert n == 0


def test_replace_day_writes_columns_and_source():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA)
    r = conn.execute(
        "SELECT source, fetched_at, iv, open_interest, vol_oi_ratio "
        "FROM option_snapshots").fetchone()
    assert r == ("cboe", FA, 0.3, 100, 2.5)


def test_replace_day_isolated_per_underlying():
    conn = db.connect(":memory:"); db.ensure_schema(conn)
    _seed(conn, "AAPL"); _seed(conn, "MSFT")
    db.replace_day(conn, "2026-07-02", "AAPL", _rows("AAPL"), FA)
    db.replace_day(conn, "2026-07-02", "MSFT", _rows("MSFT"), FA)
    # replacing AAPL must not delete MSFT's rows for the same day
    db.replace_day(conn, "2026-07-02", "AAPL", _rows("AAPL"), FA)
    n = conn.execute(
        "SELECT COUNT(*) FROM option_snapshots WHERE underlying='MSFT'"
    ).fetchone()[0]
    assert n == 1


def test_upsert_underlying_daily_upserts():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.upsert_underlying_daily(conn, "2026-07-02", _daily())
    d = dict(_daily()); d["iv30"] = 30.0
    db.upsert_underlying_daily(conn, "2026-07-02", d)
    rows = conn.execute(
        "SELECT iv30 FROM underlying_daily WHERE snapshot_date='2026-07-02'"
    ).fetchall()
    assert rows == [(30.0,)]


def test_record_day_and_stored_symbols():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.record_day(conn, "2026-07-02", "AAPL", FA, 1)
    db.record_day(conn, "2026-07-02", "AAPL", FA, 2)  # upsert
    assert conn.execute("SELECT row_count FROM days").fetchone()[0] == 2
    assert db.stored_symbols(conn) == ["AAPL"]


def test_write_snapshot_and_prune_only_headers():
    conn = db.connect(":memory:"); db.ensure_schema(conn); _seed(conn)
    db.replace_day(conn, "2026-07-02", "AAPL", _rows(), FA)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, FA, 1, 1)                            # recent
    removed = db.prune(conn, 30, FA)
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    # option history is untouched by prune
    assert conn.execute("SELECT COUNT(*) FROM option_snapshots").fetchone()[0] == 1
