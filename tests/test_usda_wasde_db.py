from sources.screeners.usda_screener import db


def _row(commodity, region, metric, my, value, unit):
    return {
        "commodity": commodity,
        "region": region,
        "metric": metric,
        "market_year": my,
        "value": value,
        "unit": unit,
        "report_date": "2025-12-09",
    }


def test_write_wasde_keeps_unit_bases_distinct_and_upserts(tmp_path):
    conn = db.connect(str(tmp_path / "w.db"))
    db.ensure_schema(conn)
    db.write_wasde(
        conn,
        [
            _row("Corn", "United States", "ending_stocks", "2025/26", 2029.0, "Million Bushels"),
            _row("Corn", "United States", "ending_stocks", "2025/26", 51.53, "Million Metric Tons"),
        ],
    )
    # the two unit bases coexist (unit is part of the key)
    assert conn.execute("SELECT COUNT(*) FROM wasde_obs").fetchone()[0] == 2
    # a re-ingest of the same key overwrites in place (revision)
    db.write_wasde(
        conn, [_row("Corn", "United States", "ending_stocks", "2025/26", 2100.0, "Million Bushels")]
    )
    assert conn.execute("SELECT COUNT(*) FROM wasde_obs").fetchone()[0] == 2
    assert (
        conn.execute("SELECT value FROM wasde_obs WHERE unit='Million Bushels'").fetchone()[0]
        == 2100.0
    )


def test_v_wasde_stocks_to_use_uses_total_use(tmp_path):
    conn = db.connect(str(tmp_path / "w.db"))
    db.ensure_schema(conn)
    db.write_wasde(
        conn,
        [
            _row("Corn", "United States", "ending_stocks", "2025/26", 2029.0, "Million Bushels"),
            _row("Corn", "United States", "total_use", "2025/26", 16280.0, "Million Bushels"),
        ],
    )
    r = conn.execute(
        "SELECT ending_stocks, total_use, stocks_to_use FROM v_wasde_stocks_to_use "
        "WHERE commodity='Corn' AND unit='Million Bushels'"
    ).fetchone()
    assert r[0] == 2029.0 and r[1] == 16280.0
    assert abs(r[2] - 2029.0 / 16280.0) < 1e-9


def test_v_wasde_stocks_to_use_falls_back_to_domestic_plus_exports(tmp_path):
    # soybeans has no single "Use, Total" line -> total_use derived from
    # domestic_use + exports on the same unit basis.
    conn = db.connect(str(tmp_path / "w.db"))
    db.ensure_schema(conn)
    db.write_wasde(
        conn,
        [
            _row("Soybeans", "United States", "ending_stocks", "2025/26", 300.0, "Million Bushels"),
            _row("Soybeans", "United States", "domestic_use", "2025/26", 2500.0, "Million Bushels"),
            _row("Soybeans", "United States", "exports", "2025/26", 1800.0, "Million Bushels"),
        ],
    )
    r = conn.execute(
        "SELECT total_use, stocks_to_use FROM v_wasde_stocks_to_use WHERE commodity='Soybeans'"
    ).fetchone()
    assert r[0] == 4300.0  # 2500 + 1800
    assert abs(r[1] - 300.0 / 4300.0) < 1e-9
