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
    counts = journal.ingest(conn, fills, [], [], NOW)
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
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["exits_attached"] == 1
    exited = conn.execute(
        "SELECT order_ref, exit_fill_date, exit_fill_price, exit_order_ref"
        " FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exited == [("b1", "2026-07-09", 99.10, "s1")]  # oldest open buy first


def test_ingest_sell_without_open_buy_is_own_decision(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (-4, 3)})])
    fills = [_fill(side="sell", order_ref="s9")]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["matched"] == 1 and counts["exits_attached"] == 0
    row = conn.execute(
        "SELECT side, composite_snapshot_id, opinion_score_sum FROM decisions"
    ).fetchone()
    assert row == ("sell", sids[0], -4)  # direction-agnostic matching


def test_ingest_duplicate_order_ref_idempotent(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [_fill()]
    journal.ingest(conn, fills, [], [], NOW)
    counts = journal.ingest(conn, fills, [], [], NOW)  # same doc replayed
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
    journal.ingest(conn, [buy, sell], [], [], NOW)
    counts = journal.ingest(conn, [sell], [], [], NOW)
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
        [],
        "2026-07-06T21:40:00+00:00",
    )
    assert counts["passes_recorded"] == 1 and counts["skipped"] == 1
    row = conn.execute(
        "SELECT symbol, action, composite_snapshot_id, opinion_score_sum,"
        " opinion_total, note, source FROM decisions"
    ).fetchone()
    assert row == ("GLD", "passed", sids[0], 4, 3, "crowded", "manual")
    # replaying the same pass is a no-op (partial unique index + OR IGNORE)
    counts = journal.ingest(conn, [], [dict(symbol="GLD", note="crowded")], [], NOW)
    assert counts["passes_recorded"] == 0


def test_ingest_writes_run_header(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_fill()], [], [], NOW, skipped=2)
    row = conn.execute(
        "SELECT ran_at, fills_seen, matched, freelance, exits_attached,"
        " passes_recorded, verdicts_recorded, duplicates_skipped, skipped"
        " FROM journal_runs"
    ).fetchone()
    assert row == (NOW, 1, 1, 0, 0, 0, 0, 0, 2)
    assert counts["run_id"] == 1


def test_manual_fill_source(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(conn, [_fill(order_ref=None)], [], [], NOW)
    assert conn.execute("SELECT source FROM decisions").fetchone()[0] == "manual"


def test_automatic_fill_recorded_but_never_matched(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    # an XLE opinion is available in-window, but a DRIP fill must not claim it
    counts = journal.ingest(conn, [_fill(placed_agent="drip")], [], [], NOW)
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
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["exits_attached"] == 1
    exited = conn.execute(
        "SELECT order_ref FROM decisions WHERE exit_fill_date IS NOT NULL"
    ).fetchall()
    assert exited == [("b1",)]  # FIFO skipped the older drip lot


def _ofill(**kw):
    """A parsed option fill as parse_doc emits it: side already directional
    for opens, broker_side the cash-sign truth, contract identity alongside."""
    base = _fill(
        symbol="XLE",
        price=2.50,
        quantity=1.0,
        order_ref="opt-1",
        contract_ref="XLE260821C00095000",
        strategy_ref=None,
        position_effect="open",
        expiration="2026-08-21",
        broker_side="buy",
        terminal=None,
    )
    base.update(kw)
    return base


def test_option_open_writes_signed_open_flow(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_ofill(broker_side="buy", terminal=None)], [], [], NOW)
    assert counts["option_flows"] == 1
    row = conn.execute(
        "SELECT decision_id, flow_date, kind, premium, contracts, cash, order_ref"
        " FROM premium_flows"
    ).fetchone()
    assert row == (1, "2026-07-07", "open", 2.50, 1.0, -250.0, "opt-1")


def test_short_open_flow_is_credit(tmp_path):
    # Sell-to-open a put: broker side sell -> credit; directional intent buy.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(
        conn,
        [_ofill(side="buy", broker_side="sell", terminal=None, price=1.20, quantity=2.0)],
        [],
        [],
        NOW,
    )
    assert conn.execute("SELECT cash FROM premium_flows").fetchone()[0] == 240.0


def test_equity_fill_writes_no_flow(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_fill()], [], [], NOW)
    assert counts["option_flows"] == 0
    assert conn.execute("SELECT COUNT(*) FROM premium_flows").fetchone()[0] == 0


def test_ingest_option_open_matches_underlying(tmp_path):
    conn, sids = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_ofill()], [], [], NOW)
    assert counts["matched"] == 1
    row = conn.execute(
        "SELECT symbol, side, contract_ref, position_effect, expiration,"
        " composite_snapshot_id FROM decisions"
    ).fetchone()
    assert row == ("XLE", "buy", "XLE260821C00095000", "open", "2026-08-21", sids[0])


def test_option_close_attaches_by_contract_not_symbol(tmp_path):
    # Two live XLE contracts; closing one must not exit the other.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(order_ref="o1", contract_ref="XLE260821C00095000"),
        _ofill(
            order_ref="o2",
            contract_ref="XLE260918C00100000",
            filled_at="2026-07-08T14:00:00+00:00",
            fill_date="2026-07-08",
        ),
        _ofill(
            order_ref="c1",
            contract_ref="XLE260918C00100000",
            position_effect="close",
            side="sell",
            price=3.10,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["exits_attached"] == 1
    rows = conn.execute(
        "SELECT order_ref, exit_fill_price FROM decisions ORDER BY order_ref"
    ).fetchall()
    assert rows == [("o1", None), ("o2", 3.10)]


def test_option_close_without_open_skips_never_creates(tmp_path):
    # Spec: a close fill never creates a decision (pre-migration opens,
    # sell-to-close ambiguity). It is skipped and counted, loudly.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    counts = journal.ingest(conn, [_ofill(position_effect="close", side="sell")], [], [], NOW)
    assert counts["skipped"] == 1 and counts["exits_attached"] == 0
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0


def test_equity_sell_never_exits_option_decision(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(order_ref="o1"),  # option open on XLE, directional buy
        _fill(
            order_ref="s1",
            side="sell",
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    journal.ingest(conn, fills, [], [], NOW)
    # the equity sell found no equity open buy: it must fall through as its
    # own (sell) decision, leaving the option row un-exited
    rows = conn.execute(
        "SELECT order_ref, exit_fill_date FROM decisions ORDER BY order_ref"
    ).fetchall()
    assert rows == [("o1", None), ("s1", None)]


def test_expiry_sweep_closes_stale_option(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(conn, [_ofill(expiration="2026-07-18")], [], [], NOW)
    # NOW maps to Phoenix 2026-07-08: not expired yet, still open
    assert (
        conn.execute("SELECT COUNT(*) FROM decisions WHERE exit_fill_date IS NULL").fetchone()[0]
        == 1
    )
    # a later run (past expiry) synthesizes the terminal event
    counts = journal.ingest(conn, [], [], [], "2026-07-20T21:40:00+00:00")
    assert counts["expired_closed"] == 1
    row = conn.execute(
        "SELECT exit_fill_date, exit_fill_price, exit_order_ref FROM decisions"
    ).fetchone()
    assert row[0] == "2026-07-18" and row[1] == 0.0
    assert row[2].startswith("expired:XLE260821C00095000")


def test_manual_option_dedup_distinguishes_contracts(tmp_path):
    # Same underlying, timestamp, side, price, quantity — different contracts.
    # The synthetic manual key must not collapse them.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(order_ref=None, contract_ref="XLE260821C00095000"),
        _ofill(order_ref=None, contract_ref="XLE260918C00100000"),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["duplicates_skipped"] == 0
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 2
    # re-ingesting the same doc is a no-op
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["duplicates_skipped"] == 2


def test_partial_close_books_flow_leaves_decision_open(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(quantity=2.0),
        _ofill(
            order_ref="c1",
            position_effect="close",
            side="sell",
            broker_side="sell",
            price=3.10,
            quantity=1.0,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["option_flows"] == 2 and counts["exits_attached"] == 0
    assert conn.execute(
        "SELECT exit_fill_date FROM decisions WHERE contract_ref IS NOT NULL"
    ).fetchone() == (None,)
    assert conn.execute(
        "SELECT kind, contracts, cash FROM premium_flows WHERE kind = 'close'"
    ).fetchone() == ("close", 1.0, 310.0)


def test_full_close_stamps_exit(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(quantity=2.0),
        _ofill(
            order_ref="c1",
            position_effect="close",
            side="sell",
            broker_side="sell",
            price=3.10,
            quantity=1.0,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
        _ofill(
            order_ref="c2",
            position_effect="close",
            side="sell",
            broker_side="sell",
            price=2.80,
            quantity=1.0,
            filled_at="2026-07-10T15:00:00+00:00",
            fill_date="2026-07-10",
        ),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["exits_attached"] == 1 and counts["option_flows"] == 3
    row = conn.execute(
        "SELECT exit_fill_date, exit_fill_price, exit_order_ref FROM decisions"
        " WHERE contract_ref IS NOT NULL"
    ).fetchone()
    assert row == ("2026-07-10", 2.80, "c2")


def test_over_close_refused_loudly(tmp_path, capsys):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(quantity=1.0),
        _ofill(
            order_ref="c1",
            position_effect="close",
            side="sell",
            broker_side="sell",
            price=3.10,
            quantity=2.0,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["skipped"] == 1 and counts["option_flows"] == 1
    assert "outstanding" in capsys.readouterr().out


def test_partial_close_reingest_is_duplicate(tmp_path):
    # c1 lives only in premium_flows (exit_order_ref never stamped) —
    # _seen must still catch it on the next sync.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    close = _ofill(
        order_ref="c1",
        position_effect="close",
        side="sell",
        broker_side="sell",
        price=3.10,
        quantity=1.0,
        filled_at="2026-07-09T15:00:00+00:00",
        fill_date="2026-07-09",
    )
    journal.ingest(conn, [_ofill(quantity=2.0), close], [], [], NOW)
    counts = journal.ingest(conn, [close], [], [], NOW)
    assert counts["duplicates_skipped"] == 1
    assert conn.execute("SELECT COUNT(*) FROM premium_flows").fetchone()[0] == 2


def test_close_of_preledger_decision_falls_back_to_single_exit(tmp_path):
    # An option decision with no open flow (pre-ledger shape): today's
    # whole-position exit behavior, no flow rows.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " quantity, order_ref, contract_ref, position_effect, expiration,"
        " recorded_at) VALUES ('XLE', 'acted', 'buy', '2026-07-07', 2.50, 1.0,"
        " 'pre-1', 'XLE260821C00095000', 'open', '2026-08-21', ?)",
        (NOW,),
    )
    close = _ofill(
        order_ref="c1",
        position_effect="close",
        side="sell",
        broker_side="sell",
        price=3.10,
        quantity=1.0,
        filled_at="2026-07-09T15:00:00+00:00",
        fill_date="2026-07-09",
    )
    counts = journal.ingest(conn, [close], [], [], NOW)
    assert counts["exits_attached"] == 1 and counts["option_flows"] == 0
    assert conn.execute("SELECT COUNT(*) FROM premium_flows").fetchone()[0] == 0


def test_expiry_sweep_books_expire_flow(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    journal.ingest(conn, [_ofill(expiration="2026-07-18", quantity=2.0)], [], [], NOW)
    counts = journal.ingest(conn, [], [], [], "2026-07-20T21:40:00+00:00")
    assert counts["expired_closed"] == 1 and counts["option_flows"] == 1
    row = conn.execute(
        "SELECT kind, premium, contracts, cash, flow_date, order_ref"
        " FROM premium_flows WHERE kind = 'expire'"
    ).fetchone()
    assert row[:5] == ("expire", 0.0, 2.0, 0.0, "2026-07-18")
    assert row[5].startswith("expired:XLE260821C00095000")


def test_expiry_sweep_partial_remainder_only(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(expiration="2026-07-18", quantity=2.0),
        _ofill(
            order_ref="c1",
            position_effect="close",
            side="sell",
            broker_side="sell",
            price=3.10,
            quantity=1.0,
            filled_at="2026-07-09T15:00:00+00:00",
            fill_date="2026-07-09",
        ),
    ]
    journal.ingest(conn, fills, [], [], NOW)
    journal.ingest(conn, [], [], [], "2026-07-20T21:40:00+00:00")
    assert conn.execute("SELECT contracts FROM premium_flows WHERE kind = 'expire'").fetchone() == (
        1.0,
    )


def test_expiry_sweep_preledger_decision_no_flow(tmp_path):
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " quantity, order_ref, contract_ref, position_effect, expiration,"
        " recorded_at) VALUES ('XLE', 'acted', 'buy', '2026-07-07', 2.50, 1.0,"
        " 'pre-1', 'XLE260821C00095000', 'open', '2026-07-18', ?)",
        (NOW,),
    )
    counts = journal.ingest(conn, [], [], [], "2026-07-20T21:40:00+00:00")
    assert counts["expired_closed"] == 1 and counts["option_flows"] == 0
    assert conn.execute("SELECT COUNT(*) FROM premium_flows").fetchone()[0] == 0


def test_assignment_dictation_books_zero_cash_flow(tmp_path):
    # Short call assigned: open credit stands as the whole premium P&L;
    # the stock leg at strike is journaled separately, never here.
    conn, _ = _scorer_with_composite(tmp_path, [("2026-07-06", {"XLE": (5, 4)})])
    fills = [
        _ofill(side="sell", broker_side="sell", price=1.20, quantity=1.0),
        _ofill(
            order_ref="a1",
            position_effect="close",
            side="buy",
            broker_side="buy",
            price=0.0,
            quantity=1.0,
            terminal="assign",
            filled_at="2026-07-17T20:00:00+00:00",
            fill_date="2026-07-17",
        ),
    ]
    counts = journal.ingest(conn, fills, [], [], NOW)
    assert counts["exits_attached"] == 1
    assert conn.execute(
        "SELECT kind, cash FROM premium_flows WHERE kind = 'assign'"
    ).fetchone() == ("assign", 0.0)
