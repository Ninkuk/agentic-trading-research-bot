from sources.screeners.eia_screener import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_series(
        conn,
        [
            {
                "series_id": "CRUDE",
                "route": "r",
                "label": "Crude",
                "category": "crude",
                "unit": "MBBL",
                "frequency": "weekly",
            }
        ],
        "t",
    )
    return conn


def test_v_latest_picks_newest_non_null():
    conn = _seed()
    db.write_observations(
        conn,
        "CRUDE",
        [
            {"period": "2026-06-19", "value": 420.0},
            {"period": "2026-06-26", "value": 415.0},
            {"period": "2026-07-03", "value": None},
        ],
    )  # withheld -> skipped
    row = conn.execute(
        "SELECT period, value, label FROM v_latest WHERE series_id='CRUDE'"
    ).fetchone()
    assert row == ("2026-06-26", 415.0, "Crude")


def test_v_weekly_change_draw_is_negative():
    conn = _seed()
    db.write_observations(
        conn,
        "CRUDE",
        [{"period": "2026-06-19", "value": 420.0}, {"period": "2026-06-26", "value": 415.0}],
    )  # a 5-MBBL draw
    row = conn.execute(
        "SELECT change_abs, change_pct FROM v_weekly_change WHERE series_id='CRUDE'"
    ).fetchone()
    assert row[0] == -5.0
    assert abs(row[1] - (-5.0 / 420.0 * 100)) < 1e-9


def test_v_series_history_full_series():
    conn = _seed()
    db.write_observations(
        conn,
        "CRUDE",
        [{"period": "2026-06-19", "value": 420.0}, {"period": "2026-06-26", "value": 415.0}],
    )
    periods = [
        r[0]
        for r in conn.execute(
            "SELECT period FROM v_series_history WHERE series_id='CRUDE' ORDER BY period"
        )
    ]
    assert periods == ["2026-06-19", "2026-06-26"]
