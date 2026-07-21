from sources.combiners.composite import db

T1 = "2026-07-05T21:00:00+00:00"
T2 = "2026-07-06T21:00:00+00:00"


def _seed(conn):
    s1 = db.write_snapshot(conn, T1, 1)
    s2 = db.write_snapshot(conn, T2, 1)
    for sid, score in ((s1, 1), (s2, 2)):
        db.write_signal_values(
            conn,
            sid,
            [
                dict(
                    signal_id=f"sig{i}",
                    grain="ticker",
                    entity="GME",
                    raw_value=1.0,
                    score=score,
                    obs_date="2026-07-03",
                    staleness_days=1.0,
                )
                for i in range(3)
            ],
        )
        db.write_signal_values(
            conn,
            sid,
            [
                dict(
                    signal_id="sig0",
                    grain="ticker",
                    entity="AAPL",
                    raw_value=1.0,
                    score=1,
                    obs_date="2026-07-03",
                    staleness_days=1.0,
                )
            ],
        )
        db.write_ticker_scores(conn, sid)
        db.write_market_regime(conn, sid, {})
    return s1, s2


def test_latest_views_pick_newest_snapshot(tmp_path):
    conn = db.connect(str(tmp_path / "c.db"))
    db.ensure_schema(conn)
    s1, s2 = _seed(conn)
    assert conn.execute("SELECT id FROM v_latest_snapshot").fetchone()[0] == s2
    assert conn.execute("SELECT COUNT(*) FROM v_latest_regime").fetchone()[0] == 1
    assert {r[0] for r in conn.execute("SELECT symbol FROM v_latest_scorecard")} == {"GME", "AAPL"}


def test_flagged_applies_both_thresholds(tmp_path):
    conn = db.connect(str(tmp_path / "c.db"))
    db.ensure_schema(conn)
    _seed(conn)
    # GME latest: 3 signals x score 2 -> score_sum 6, total 3 -> flagged
    # AAPL: 1 signal, score_sum 1 -> not flagged
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_flagged")] == ["GME"]


def test_score_history_spans_snapshots(tmp_path):
    conn = db.connect(str(tmp_path / "c.db"))
    db.ensure_schema(conn)
    _seed(conn)
    got = conn.execute(
        "SELECT captured_at, score_sum FROM v_score_history WHERE symbol='GME' ORDER BY captured_at"
    ).fetchall()
    assert got == [(T1, 3), (T2, 6)]


def test_flagged_isolates_each_threshold(tmp_path):
    """Verify v_flagged applies both thresholds (|score_sum| >= 3, total >= 2).

    With per-signal scores capped at +/-2, |score_sum| >= 3 already implies
    total >= 2, so "passes sum, fails total" is unconstructible — the total
    gate is belt-and-braces against a future widening of the score range.
    - SINGLE_MAX: one signal at the +2 cap -> score_sum=2, total=1 -> not flagged
    - LOWSUM_HIGHTOT: score_sum=2 (fails sum), total=2 (passes total) -> not flagged
    - AT_BOUNDARY: score_sum=3, total=2 -> flagged (both at boundary)
    - NEG_BOUNDARY: score_sum=-3, total=2 -> flagged (ABS applies)
    """
    conn = db.connect(str(tmp_path / "c2.db"))
    db.ensure_schema(conn)
    sid = db.write_snapshot(conn, T2, 1)

    cases = {
        "SINGLE_MAX": [2],
        "LOWSUM_HIGHTOT": [1, 1],
        "AT_BOUNDARY": [2, 1],
        "NEG_BOUNDARY": [-2, -1],
    }
    for entity, scores in cases.items():
        db.write_signal_values(
            conn,
            sid,
            [
                dict(
                    signal_id=f"s{i}",
                    grain="ticker",
                    entity=entity,
                    raw_value=1.0,
                    score=score,
                    obs_date="2026-07-03",
                    staleness_days=1.0,
                )
                for i, score in enumerate(scores)
            ],
        )

    db.write_ticker_scores(conn, sid)

    # Only AT_BOUNDARY and NEG_BOUNDARY should pass both thresholds
    flagged = sorted(r[0] for r in conn.execute("SELECT symbol FROM v_flagged"))
    assert flagged == ["AT_BOUNDARY", "NEG_BOUNDARY"]
