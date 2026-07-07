from sources.combiners.scorer import db

NOW = "2026-07-20T21:10:00+00:00"


def _seeded(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-03', '2026-07-06', ?, 2, 0, 0)",
        (NOW,),
    )
    conn.execute(  # weekend sibling: marker-only, same window
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (2, '2026-07-05', '2026-07-06', ?, 0, 0, 0)",
        (NOW,),
    )
    for sym, score in (("XLE", 5), ("GLD", 4)):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
            " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
            " entry_close, bench_entry_close, exit_date, exit_close, fwd_return,"
            " bench_fwd_return, matured_at)"
            " VALUES (1, '2026-07-03', ?, ?, 4, 4, 0, 5, '2026-07-06',"
            " 100.0, 500.0, '2026-07-13', 104.0, 0.04, 0.01, ?)",
            (sym, score, NOW),
        )
    conn.commit()
    return conn


def _decide(conn, **kw):
    cols = dict(
        symbol="XLE",
        action="acted",
        side="buy",
        composite_snapshot_id=1,
        composite_date="2026-07-03",
        opinion_score_sum=5,
        opinion_total=4,
        fill_date="2026-07-06",
        fill_price=101.0,
        recorded_at=NOW,
    )
    cols.update(kw)
    keys = [k for k, v in cols.items() if v is not None]
    conn.execute(
        f"INSERT INTO decisions ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
        [cols[k] for k in keys],
    )
    conn.commit()


def test_decision_outcomes_slippage_and_paper_legs(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)
    row = conn.execute(
        "SELECT entry_slippage, fwd_return, bench_fwd_return, aligned,"
        " realized_return, fill_lag_days FROM v_decision_outcomes"
        " WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - 0.01) < 1e-9  # paid 101 vs paper 100 = +1% cost
    assert row[1] == 0.04 and row[2] == 0.01
    assert row[3] == 1  # buy on a bull opinion
    assert row[4] is None  # no exit yet
    assert row[5] == 0.0  # filled on the paper entry date


def test_decision_outcomes_realized_round_trip(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, exit_fill_date="2026-07-13", exit_fill_price=103.0)
    row = conn.execute(
        "SELECT realized_return FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - (103.0 / 101.0 - 1)) < 1e-9


def test_decision_outcomes_sell_slippage_sign(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, side="sell", fill_price=99.0)
    row = conn.execute(
        "SELECT entry_slippage, aligned FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert abs(row[0] - 0.01) < 1e-9  # sold at 99 vs paper 100: 1% cost
    assert row[1] == 0  # sell against a bull flag


def test_window_rekeying_marker_only_snapshot(tmp_path):
    conn = _seeded(tmp_path)
    # decision matched to Sunday's marker-only snapshot 2, whose rerun score
    # FLIPPED bearish vs Friday's owner (bull, score 5)
    _decide(
        conn,
        composite_snapshot_id=2,
        composite_date="2026-07-05",
        opinion_score_sum=-4,
        opinion_total=3,
    )
    row = conn.execute(
        "SELECT fwd_return, aligned, owner_score_sum FROM v_decision_outcomes WHERE horizon = 5"
    ).fetchone()
    assert row[0] == 0.04  # paper legs graded against the owning snapshot
    assert row[1] == 0  # ...but alignment judged vs the opinion the human SAW
    assert row[2] == 5  # owner's score exposed alongside


def test_freelance_rows_have_null_paper_legs(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn, symbol="NVDA", composite_snapshot_id=None, composite_date=None)
    rows = conn.execute(
        "SELECT fwd_return, entry_slippage FROM v_decision_outcomes WHERE symbol = 'NVDA'"
    ).fetchall()
    assert rows == [(None, None)]
    assert conn.execute("SELECT symbol FROM v_freelance").fetchall() == [("NVDA",)]


def test_flag_response_three_states(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)  # acted on XLE; GLD has no row -> inferred pass
    rows = dict(conn.execute("SELECT symbol, response FROM v_flag_response").fetchall())
    assert rows == {"XLE": "acted", "GLD": "passed_inferred"}
    _decide(conn, symbol="GLD", action="passed", side=None, fill_date=None, fill_price=None)
    rows = dict(conn.execute("SELECT symbol, response FROM v_flag_response").fetchall())
    assert rows["GLD"] == "passed"


def test_flag_response_ignores_nonaligned_sell(tmp_path):
    conn = _seeded(tmp_path)
    # exit-shaped sell (pre-journal holding, or a scale-out second lot) that
    # matched the bull flag's window: must NOT count as acting on the flag
    _decide(conn, side="sell", fill_price=99.0)
    rows = dict(conn.execute("SELECT symbol, response FROM v_flag_response").fetchall())
    assert rows["XLE"] == "passed_inferred"
    # ...but a direction-aligned sell answers a BEAR flag; simulate by
    # checking the buy case is unaffected
    _decide(conn, order_ref="b-real")
    rows = dict(conn.execute("SELECT symbol, response FROM v_flag_response").fetchall())
    assert rows["XLE"] == "acted"


def test_flag_response_rekeys_pass_on_sibling_snapshot(tmp_path):
    conn = _seeded(tmp_path)
    _decide(
        conn,
        symbol="GLD",
        action="passed",
        side=None,
        fill_date=None,
        fill_price=None,
        composite_snapshot_id=2,
        composite_date="2026-07-05",
    )
    rows = dict(conn.execute("SELECT symbol, response FROM v_flag_response").fetchall())
    assert rows["GLD"] == "passed"  # Sunday's pass answers Friday's graded flag


def test_human_filter_aggregates(tmp_path):
    conn = _seeded(tmp_path)
    _decide(conn)
    rows = {
        r[0]: (r[2], r[3])
        for r in conn.execute("SELECT response, horizon, n, avg_dir_excess FROM v_human_filter")
    }
    assert rows["acted"] == (1, 0.03)  # bull flag: 0.04 - 0.01
    assert rows["passed_inferred"] == (1, 0.03)


def test_placed_agent_exposed_in_views(tmp_path):
    conn = _seeded(tmp_path)
    _decide(
        conn,
        symbol="NVDA",
        composite_snapshot_id=None,
        composite_date=None,
        opinion_score_sum=None,
        opinion_total=None,
        placed_agent="drip",
    )
    assert conn.execute("SELECT placed_agent FROM v_freelance").fetchone() == ("drip",)
    assert conn.execute(
        "SELECT placed_agent FROM v_decision_outcomes WHERE symbol = 'NVDA'"
    ).fetchone() == ("drip",)
