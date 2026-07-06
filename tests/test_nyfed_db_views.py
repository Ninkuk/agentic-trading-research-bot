from sources.screeners.nyfed_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _rate(rate_type, d, rate):
    return {
        "rate_type": rate_type,
        "effective_date": d,
        "percent_rate": rate,
        "volume_bn": None,
        "pct_1": None,
        "pct_25": None,
        "pct_75": None,
        "pct_99": None,
    }


def test_v_sofr_latest_spread_null_then_computed():
    conn = _fresh()
    db.write_reference_rates(
        conn, [_rate("SOFR", "2026-06-01", 5.30), _rate("SOFR", "2026-06-02", 5.31)]
    )
    row = conn.execute("SELECT effective_date, sofr_iorb_spread FROM v_sofr_latest").fetchone()
    assert row[0] == "2026-06-02" and row[1] is None  # no IORB -> NULL
    conn.execute("INSERT INTO iorb VALUES ('2026-06-01', 5.15)")
    conn.commit()
    row = conn.execute("SELECT sofr_iorb_spread FROM v_sofr_latest").fetchone()
    assert abs(row[0] - 0.16) < 1e-9  # 5.31 - 5.15


def test_v_rrp_trend_take_up_and_change():
    conn = _fresh()
    db.write_repo_ops(
        conn,
        [
            {
                "operation_id": "A",
                "operation_date": "2026-06-01",
                "operation_type": "reverse_repo",
                "total_submitted": None,
                "total_accepted": 400.0,
                "award_rate": None,
            },
            {
                "operation_id": "B",
                "operation_date": "2026-06-02",
                "operation_type": "reverse_repo",
                "total_submitted": None,
                "total_accepted": 500.0,
                "award_rate": None,
            },
        ],
    )
    row = conn.execute(
        "SELECT change_vs_prior FROM v_rrp_trend WHERE operation_date='2026-06-02'"
    ).fetchone()
    assert row[0] == 100.0


def test_v_soma_runoff_wow_change():
    conn = _fresh()
    db.write_soma_holdings(
        conn,
        [
            {"as_of_date": "2026-05-28", "security_type": "total", "par_value": 7.2e12},
            {"as_of_date": "2026-06-04", "security_type": "total", "par_value": 7.15e12},
        ],
    )
    row = conn.execute(
        "SELECT wow_change FROM v_soma_runoff WHERE as_of_date='2026-06-04'"
    ).fetchone()
    assert abs(row[0] - (-5e10)) < 1e6  # runoff (negative)
