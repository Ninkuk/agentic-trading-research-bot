from sources.combiners.composite import db

NOW = "2026-07-06T21:00:00+00:00"
OLD = "2025-07-01T21:00:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    return conn


def _row(**kw):
    base = dict(
        signal_id="s1",
        grain="ticker",
        entity="AAPL",
        raw_value=1.0,
        score=1,
        obs_date="2026-07-03",
        staleness_days=3.0,
    )
    base.update(kw)
    return base


def test_snapshot_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, signals_expected=5)
    db.finish_snapshot(conn, sid, ok=4, failed=1)
    got = conn.execute(
        "SELECT captured_at, signals_expected, signals_ok,"
        " signals_failed FROM snapshots WHERE id=?",
        (sid,),
    ).fetchone()
    assert got == (NOW, 5, 4, 1)


def test_write_signal_values_ignores_dupes(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    n = db.write_signal_values(conn, sid, [_row(), _row()])
    assert n == 1


def test_apply_crosswalk_fans_out(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [_row(signal_id="cftc_mm_extreme", grain="asset_class", entity="energy", score=2)],
    )
    n = db.apply_crosswalk(conn, sid, {"energy": ["XLE", "XOM"]})
    assert n == 2
    got = conn.execute(
        "SELECT entity, score, via_crosswalk FROM signal_values"
        " WHERE snapshot_id=? AND grain='ticker' ORDER BY entity",
        (sid,),
    ).fetchall()
    assert got == [("XLE", 2, 1), ("XOM", 2, 1)]


def test_write_ticker_scores_counts_and_portfolio(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 4)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(signal_id="a", entity="AAPL", score=2, staleness_days=3.0),
            _row(signal_id="b", entity="AAPL", score=-1, staleness_days=9.0),
            _row(signal_id="a", entity="XOM", score=1),
            _row(signal_id="portfolio_holding", entity="XOM", score=0),
            _row(signal_id="portfolio_holding", entity="DHR", score=0),
        ],
    )
    db.write_ticker_scores(conn, sid)
    rows = {
        r[0]: r[1:]
        for r in conn.execute(
            "SELECT symbol, bullish, bearish, total, score_sum, coverage,"
            " worst_staleness_days, in_portfolio FROM ticker_scores"
            " WHERE snapshot_id=?",
            (sid,),
        )
    }
    # 2 distinct non-informational ticker signals ran (a, b)
    assert rows["AAPL"] == (1, 1, 2, 1, 1.0, 9.0, 0)
    assert rows["XOM"] == (1, 0, 1, 1, 0.5, 3.0, 1)
    assert rows["DHR"] == (0, 0, 0, 0, 0.0, None, 1)  # held, no signals


def test_apply_crosswalk_direct_row_wins(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(
                signal_id="cftc_mm_extreme", grain="ticker", entity="XLE", score=-1, via_crosswalk=0
            ),
            _row(signal_id="cftc_mm_extreme", grain="asset_class", entity="energy", score=2),
        ],
    )
    n = db.apply_crosswalk(conn, sid, {"energy": ["XLE", "XOM"]})
    assert n == 1
    got = {
        r[0]: r[1:]
        for r in conn.execute(
            "SELECT entity, score, via_crosswalk FROM signal_values"
            " WHERE snapshot_id=? AND grain='ticker'",
            (sid,),
        )
    }
    assert got["XLE"] == (-1, 0)
    assert got["XOM"] == (2, 1)


def test_write_market_regime_risk_off(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(signal_id="cboe_vix", grain="market", entity="*", raw_value=31.0, score=2),
            _row(signal_id="fred_hy_spread", grain="market", entity="*", raw_value=5.5, score=2),
        ],
    )
    db.write_market_regime(conn, sid, {"cboe_vix": "vix", "fred_hy_spread": "hy_spread"})
    got = conn.execute(
        "SELECT vix, hy_spread, regime, inputs_expected, inputs_present"
        " FROM market_regime WHERE snapshot_id=?",
        (sid,),
    ).fetchone()
    assert got == (31.0, 5.5, "risk_off", 2, 2)


def test_write_market_regime_risk_on(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(signal_id="cboe_vix", grain="market", entity="*", raw_value=15.0, score=0),
            _row(signal_id="fred_hy_spread", grain="market", entity="*", raw_value=2.5, score=0),
        ],
    )
    db.write_market_regime(conn, sid, {"cboe_vix": "vix", "fred_hy_spread": "hy_spread"})
    got = conn.execute(
        "SELECT vix, hy_spread, regime, inputs_expected, inputs_present"
        " FROM market_regime WHERE snapshot_id=?",
        (sid,),
    ).fetchone()
    assert got == (15.0, 2.5, "risk_on", 2, 2)


def test_write_market_regime_mixed_when_signal_missing(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(signal_id="cboe_vix", grain="market", entity="*", raw_value=15.0, score=0),
        ],
    )
    db.write_market_regime(conn, sid, {"cboe_vix": "vix", "fred_hy_spread": "hy_spread"})
    got = conn.execute(
        "SELECT vix, hy_spread, regime, inputs_expected, inputs_present"
        " FROM market_regime WHERE snapshot_id=?",
        (sid,),
    ).fetchone()
    assert got == (15.0, None, "mixed", 2, 1)


def test_write_market_regime_null_raw_value_not_present(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(
        conn,
        sid,
        [
            _row(signal_id="cboe_vix", grain="market", entity="*", raw_value=None, score=0),
        ],
    )
    db.write_market_regime(conn, sid, {"cboe_vix": "vix"})
    got = conn.execute(
        "SELECT vix, inputs_present FROM market_regime WHERE snapshot_id=?", (sid,)
    ).fetchone()
    assert got == (None, 0)


def test_prune_cascades_all_children(tmp_path):
    conn = _conn(tmp_path)
    old = db.write_snapshot(conn, OLD, 1)
    db.write_signal_values(conn, old, [_row()])
    db.write_ticker_scores(conn, old)
    db.write_market_regime(conn, old, {})
    db.write_snapshot(conn, NOW, 1)
    assert db.prune(conn, keep_days=90, now_iso=NOW) == 1
    for t in ("signal_values", "market_regime", "ticker_scores"):
        assert (
            conn.execute(f"SELECT COUNT(*) FROM {t} WHERE snapshot_id=?", (old,)).fetchone()[0] == 0
        )
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
