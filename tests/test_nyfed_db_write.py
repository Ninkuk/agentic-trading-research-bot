from sources.screeners.nyfed_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_reference_rates_upsert_in_place():
    conn = _fresh()
    row = {
        "rate_type": "SOFR",
        "effective_date": "2026-06-01",
        "percent_rate": 5.31,
        "volume_bn": 2100.0,
        "pct_1": None,
        "pct_25": None,
        "pct_75": None,
        "pct_99": None,
    }
    db.write_reference_rates(conn, [row])
    db.write_reference_rates(conn, [{**row, "percent_rate": 5.35}])  # restated
    got = conn.execute("SELECT percent_rate FROM reference_rates").fetchall()
    assert got == [(5.35,)]


def test_write_repo_ops_dedupe_and_null_blank():
    conn = _fresh()
    n = db.write_repo_ops(
        conn,
        [
            {
                "operation_id": "R1",
                "operation_date": "2026-06-01",
                "operation_type": "repo",
                "total_submitted": 100.0,
                "total_accepted": None,
                "award_rate": None,
            },
            {
                "operation_id": "R1",
                "operation_date": "2026-06-01",
                "operation_type": "repo",
                "total_submitted": 200.0,
                "total_accepted": None,
                "award_rate": None,
            },
        ],
    )
    assert n == 1
    assert conn.execute("SELECT total_submitted FROM repo_ops").fetchone()[0] == 200.0
    assert conn.execute("SELECT total_accepted FROM repo_ops").fetchone()[0] is None


def test_prune_deletes_snapshots_not_facts():
    conn = _fresh()
    db.write_soma_holdings(
        conn, [{"as_of_date": "2026-06-03", "security_type": "total", "par_value": 7e12}]
    )
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM soma_holdings").fetchone()[0] == 1
