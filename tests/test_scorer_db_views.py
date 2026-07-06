from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"
DAYS = [
    "2026-06-25",
    "2026-06-26",
    "2026-06-29",
    "2026-06-30",
    "2026-07-01",
    "2026-07-02",
    "2026-07-06",
    "2026-07-07",
]


def _seed(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # WIN rises faster than SPY; LOSE falls; SPY drifts up
    db.insert_prices(conn, [("WIN", d, 100 + 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("LOSE", d, 100 - 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("SPY", d, 500 + i) for i, d in enumerate(DAYS)])
    db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [
            dict(
                symbol="WIN",
                score_sum=4,
                total=3,
                bullish=3,
                bearish=0,
                in_portfolio=0,
            ),
            dict(
                symbol="LOSE",
                score_sum=-4,
                total=3,
                bullish=0,
                bearish=3,
                in_portfolio=0,
            ),
            dict(
                symbol="SPY",
                score_sum=1,
                total=1,
                bullish=1,
                bearish=0,
                in_portfolio=0,
            ),
        ],
        [
            dict(
                signal_id="si_days_to_cover",
                entity="WIN",
                score=2,
                via_crosswalk=0,
            ),
            dict(
                signal_id="sv_ratio_spike",
                entity="LOSE",
                score=-2,
                via_crosswalk=0,
            ),
        ],
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
    )
    db.mature(conn, NOW)
    return conn


def test_bucket_performance(tmp_path):
    conn = _seed(tmp_path)
    rows = {
        r[0]: r
        for r in conn.execute(
            "SELECT bucket, horizon, n_matured, avg_excess, hit_rate FROM v_bucket_performance"
        )
    }
    assert rows["strong_bull"][2] == 1 and rows["strong_bull"][3] > 0
    assert rows["strong_bull"][4] == 1.0  # WIN beat SPY
    assert rows["strong_bear"][2] == 1
    assert rows["strong_bear"][4] == 1.0  # LOSE lagged SPY = bear hit
    assert rows["thin"][2] == 1  # single-signal SPY row


def test_signal_efficacy_direction_adjusted(tmp_path):
    conn = _seed(tmp_path)
    rows = {
        r[0]: r
        for r in conn.execute(
            "SELECT signal_id, n_matured, avg_directional_excess, hit_rate FROM v_signal_efficacy"
        )
    }
    # both signals called their direction correctly -> positive adj excess
    assert rows["si_days_to_cover"][2] > 0
    assert rows["sv_ratio_spike"][2] > 0
    assert rows["sv_ratio_spike"][3] == 1.0


def test_regime_and_pending(tmp_path):
    conn = _seed(tmp_path)
    r = conn.execute(
        "SELECT regime, n_matured, avg_bench_return FROM v_regime_performance"
    ).fetchone()
    assert r[0] == "risk_on" and r[1] == 1 and r[2] > 0
    # register something unmaturable -> shows in v_pending
    db.register_snapshot(conn, 2, "2026-07-07", [], [], "mixed", (21,), "SPY", 7, NOW)
    assert conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0] == 1


def test_v_basis_breaks_flags_split_only(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # ACME splits 2:1 between DAYS[2] and DAYS[3]; SPY is normal noise.
    closes = [100.0, 101.0, 99.0, 49.6, 50.0, 50.4, 49.9, 50.2]
    db.insert_prices(conn, list(zip(["ACME"] * 8, DAYS, closes, strict=True)))
    db.insert_prices(conn, [("SPY", d, 500 + i) for i, d in enumerate(DAYS)])
    rows = conn.execute(
        "SELECT symbol, prev_date, price_date, ratio FROM v_basis_breaks"
    ).fetchall()
    assert len(rows) == 1
    sym, prev_date, price_date, ratio = rows[0]
    assert (sym, prev_date, price_date) == ("ACME", DAYS[2], DAYS[3])
    assert abs(ratio - 49.6 / 99.0) < 1e-9
