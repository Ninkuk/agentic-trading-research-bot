from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db, journal

NOW = "2026-07-08T21:40:00+00:00"


def _mini_composite(path, opinions):
    """opinions: list of (date, {symbol: (score_sum, total)}). captured_at is
    written as <date>T21:05:00+00:00, which the Phoenix shift maps back to
    <date> — same convention as test_scorer_run."""
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    sids = []
    for date, scores in opinions:
        conn.execute(
            "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, 1)",
            (f"{date}T21:05:00+00:00",),
        )
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for sym, (score_sum, total) in scores.items():
            conn.execute(
                "INSERT INTO ticker_scores (snapshot_id, symbol, total, score_sum)"
                " VALUES (?, ?, ?, ?)",
                (sid, sym, total, score_sum),
            )
        sids.append(sid)
    conn.commit()
    conn.close()
    return sids


def _scorer_with_composite(tmp_path, opinions):
    sids = _mini_composite(tmp_path / "composite.db", opinions)
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{tmp_path / 'composite.db'}?mode=ro",))
    return conn, sids


def _fill(**kw):
    base = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2.0,
        filled_at="2026-07-07T14:31:00+00:00",
        fill_date="2026-07-07",
        order_ref="ref-1",
        note=None,
    )
    base.update(kw)
    return base


def test_match_most_recent_in_window(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-02", {"XLE": (5, 4)}), ("2026-07-06", {"XLE": (4, 3)})],
    )
    assert journal.match_opinion(conn, "XLE", "2026-07-07") == (sids[1], "2026-07-06", 4, 3)


def test_match_window_edges(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-02", {"XLE": (5, 4)})])
    # day 5 after the opinion: still matchable
    assert journal.match_opinion(conn, "XLE", "2026-07-07") == (sids[0], "2026-07-02", 5, 4)
    # day 6: expired
    assert journal.match_opinion(conn, "XLE", "2026-07-08") is None
    # same-day fill: the opinion forms at 9:05pm, after the close — excluded
    assert journal.match_opinion(conn, "XLE", "2026-07-02") is None


def test_match_requires_symbol_scored(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    assert journal.match_opinion(conn, "GLD", "2026-07-07") is None


def test_match_flagged_needs_thresholds(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-05", {"GLD": (2, 2)}), ("2026-07-06", {"GLD": (3, 2)})],
    )
    # score 2 isn't a flag; the 07-06 flag matches, and same-day is allowed
    assert journal.match_flagged(conn, "GLD", "2026-07-06") == (sids[1], "2026-07-06", 3, 2)
    assert journal.match_flagged(conn, "GLD", "2026-07-05") is None


def test_flag_thresholds_pinned_to_composite_view():
    # ONE definition (db.py) feeds both the matcher and v_flag_response;
    # this pins it to composite's hand-tunable v_flagged text.
    assert f"ABS(score_sum) >= {db.FLAG_MIN_ABS_SCORE}" in composite_db._SCHEMA
    assert f"total >= {db.FLAG_MIN_TOTAL}" in composite_db._SCHEMA


def test_ingest_buy_matched_and_freelance(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [_fill(), _fill(symbol="NVDA", order_ref="ref-2")]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["matched"] == 1 and counts["freelance"] == 1
    rows = conn.execute(
        "SELECT symbol, composite_snapshot_id, composite_date,"
        " opinion_score_sum, opinion_total, source"
        " FROM decisions ORDER BY symbol"
    ).fetchall()
    assert rows[0] == ("NVDA", None, None, None, None, "mcp")
    assert rows[1] == ("XLE", sids[0], "2026-07-06", 5, 4, "mcp")


def test_ingest_sell_attaches_fifo_exit(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _fill(order_ref="b1", filled_at="2026-07-07T14:00:00+00:00"),
        _fill(order_ref="b2", filled_at="2026-07-08T14:00:00+00:00", fill_date="2026-07-08"),
        _fill(
            order_ref="s1",
            side="sell",
            price=99.10,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["exits_attached"] == 1
    exited = conn.execute(
        "SELECT order_ref, exit_fill_date, exit_fill_price, exit_order_ref"
        " FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exited == [("b1", "2026-07-09", 99.10, "s1")]  # oldest open buy first


def test_ingest_sell_without_open_buy_is_own_decision(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (-4, 3)})])
    fills = [_fill(side="sell", order_ref="s9")]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["matched"] == 1 and counts["exits_attached"] == 0
    row = conn.execute(
        "SELECT side, composite_snapshot_id, opinion_score_sum FROM decisions"
    ).fetchone()
    assert row == ("sell", sids[0], -4)  # direction-agnostic matching


def test_ingest_duplicate_order_ref_idempotent(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [_fill()]
    journal.ingest(conn, fills, [], NOW)
    counts = journal.ingest(conn, fills, [], NOW)  # same doc replayed
    assert counts["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_ingest_exit_ref_also_dedupes(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    buy = _fill(order_ref="b1")
    sell = _fill(
        order_ref="s1",
        side="sell",
        filled_at="2026-07-08T15:00:00+00:00",
        fill_date="2026-07-08",
    )
    journal.ingest(conn, [buy, sell], [], NOW)
    counts = journal.ingest(conn, [sell], [], NOW)
    assert counts["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_ingest_pass_needs_flag(tmp_path):
    conn, sids = _scorer_with_composite(
        tmp_path,
        [("2026-07-06", {"GLD": (4, 3), "TLT": (1, 3)})],
    )
    counts = journal.ingest(
        conn,
        [],
        [dict(symbol="GLD", note="crowded"), dict(symbol="TLT", note=None)],
        "2026-07-06T21:40:00+00:00",
    )
    assert counts["passes_recorded"] == 1 and counts["skipped"] == 1
    row = conn.execute(
        "SELECT symbol, action, composite_snapshot_id, opinion_score_sum,"
        " opinion_total, note, source FROM decisions"
    ).fetchone()
    assert row == ("GLD", "passed", sids[0], 4, 3, "crowded", "manual")
    # replaying the same pass is a no-op (partial unique index + OR IGNORE)
    counts = journal.ingest(conn, [], [dict(symbol="GLD", note="crowded")], NOW)
    assert counts["passes_recorded"] == 0


def test_ingest_writes_run_header(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_fill()], [], NOW, skipped=2)
    row = conn.execute(
        "SELECT ran_at, fills_seen, matched, freelance, exits_attached,"
        " passes_recorded, duplicates_skipped, skipped FROM journal_runs"
    ).fetchone()
    assert row == (NOW, 1, 1, 0, 0, 0, 0, 2)
    assert counts["run_id"] == 1


def test_manual_fill_source(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(conn, [_fill(order_ref=None)], [], NOW)
    assert conn.execute("SELECT source FROM decisions").fetchone()[0] == "manual"


def test_automatic_fill_recorded_but_never_matched(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    # an XLE opinion is available in-window, but a DRIP fill must not claim it
    counts = journal.ingest(conn, [_fill(placed_agent="drip")], [], NOW)
    assert counts["matched"] == 0 and counts["freelance"] == 1
    row = conn.execute("SELECT composite_snapshot_id, placed_agent FROM decisions").fetchone()
    assert row == (None, "drip")


def test_sell_never_exits_automatic_buy(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _fill(order_ref="d1", placed_agent="drip"),  # oldest open buy, but automatic
        _fill(order_ref="b1", filled_at="2026-07-08T14:00:00+00:00", fill_date="2026-07-08"),
        _fill(
            order_ref="s1",
            side="sell",
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], NOW)
    assert counts["exits_attached"] == 1
    exited = conn.execute(
        "SELECT order_ref FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exited == [("b1",)]  # FIFO skipped the older drip lot
