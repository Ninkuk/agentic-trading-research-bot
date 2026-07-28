import pytest

from sources.monitors.market_calendar import db as cal_db
from sources.screeners.orders import db as orders_db
from sources.screeners.orders import run

SUMMER_OPEN = "2026-07-27T13:35:00+00:00"  # Monday, inside window
ENV = {
    "ROBINHOOD_ACCOUNT_NUMBER": "TESTACCT0",
    "ORDERS_MAX_ORDER_NOTIONAL": "5000",
    "ORDERS_MAX_DAILY_NOTIONAL": "8000",
    "ORDERS_CASH_FLOOR": "500",
    "ORDERS_ALLOW_NONINTERACTIVE": "1",
}


@pytest.fixture
def dbs(tmp_path):
    orders_path = str(tmp_path / "orders.db")
    cal_path = str(tmp_path / "market_calendar.db")
    conn = cal_db.connect(cal_path)
    cal_db.ensure_schema(conn)
    # Seed one future holiday so preflight is not calendar-blind.
    conn.execute(
        "INSERT INTO events (event_type, event_date, subtype, title, source, fetched_at)"
        " VALUES ('market_holiday', '2026-12-25', '', 'Christmas', 'test', 't')"
    )
    conn.commit()
    conn.close()
    return orders_path, cal_path


def _queue(orders_path, cal_path, symbol="TSLA", qty=10, ref=310.0, gap=3.0, expires="2026-07-27"):
    return run.run_queue(
        orders_path,
        cal_path,
        symbol,
        qty,
        ref,
        gap,
        expires,
        note="test",
        now_iso="2026-07-27T02:00:00+00:00",
        stdin_isatty=True,
        env=ENV,
    )


def _plan_doc(ask=312.0, cash=9000.0, ts="2026-07-27T13:34:30+00:00", symbol="TSLA"):
    return {
        "as_of": SUMMER_OPEN,
        "quotes": [{"symbol": symbol, "ask": ask, "quote_ts": ts}],
        "portfolio": {"settled_cash": cash},
    }


def test_happy_path_plans_with_capped_limit(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    (o,) = plan["orders"]
    # min(312*1.002, 310*1.03) = min(312.624, 319.30) -> 312.62 (ROUND_DOWN)
    assert o == {
        "queue_id": qid,
        "symbol": "TSLA",
        "qty": "10",
        "limit_price": "312.62",
        "ref_id": o["ref_id"],
    }
    assert plan["account_number"] == "TESTACCT0"


def test_gap_veto(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, ref=300.0, gap=3.0)  # ceiling 309
    plan = run.run_plan(orders_path, cal_path, _plan_doc(ask=312.0), SUMMER_OPEN, ENV)
    assert plan["orders"] == []
    conn = orders_db.connect(orders_path)
    status, reason = conn.execute("SELECT status, resolution_reason FROM queue").fetchone()
    assert status == "vetoed" and "gapped" in reason


def test_stale_quote_vetoes_only_that_row(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, symbol="TSLA")
    _queue(orders_path, cal_path, symbol="AAPL", ref=200.0)
    doc = {
        "as_of": SUMMER_OPEN,
        "quotes": [
            {"symbol": "TSLA", "ask": 311.0, "quote_ts": "2026-07-27T13:20:00+00:00"},  # 15m old
            {"symbol": "AAPL", "ask": 201.0, "quote_ts": "2026-07-27T13:34:30+00:00"},
        ],
        "portfolio": {"settled_cash": 9000.0},
    }
    plan = run.run_plan(orders_path, cal_path, doc, SUMMER_OPEN, ENV)
    assert [o["symbol"] for o in plan["orders"]] == ["AAPL"]


def test_missing_ask_vetoes(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(ask=None, ts=None), SUMMER_OPEN, ENV)
    assert plan["orders"] == []


def test_daily_cap_and_cash_floor_veto_the_breaching_row_only(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, symbol="AAA", qty=10, ref=310.0)  # ~3126 notional
    _queue(orders_path, cal_path, symbol="BBB", qty=10, ref=310.0)  # ~3126, total ~6252
    _queue(orders_path, cal_path, symbol="CCC", qty=10, ref=310.0)  # would breach 8000 daily
    doc = {
        "as_of": SUMMER_OPEN,
        "quotes": [
            {"symbol": s, "ask": 312.0, "quote_ts": "2026-07-27T13:34:30+00:00"}
            for s in ("AAA", "BBB", "CCC")
        ],
        "portfolio": {"settled_cash": 20000.0},
    }
    plan = run.run_plan(orders_path, cal_path, doc, SUMMER_OPEN, ENV)
    assert [o["symbol"] for o in plan["orders"]] == ["AAA", "BBB"]


def test_expired_row_never_plans(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, expires="2026-07-24")
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    assert plan["orders"] == []


def test_expiry_uses_phoenix_date_not_utc_slice(dbs):
    # 04:12 UTC on the 28th is still the 27th in Phoenix — a row expiring
    # on the 27th must NOT be flipped to expired by an out-of-window run.
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path, expires="2026-07-27")
    run.run_plan(orders_path, cal_path, _plan_doc(), "2026-07-28T04:12:00+00:00", ENV)
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT status FROM queue WHERE id=?", (qid,)).fetchone()[0] == "queued"


def test_plan_outside_window_is_empty_and_claims_nothing(dbs):
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), "2026-07-27T20:00:00+00:00", ENV)
    assert plan["orders"] == []


def test_second_plan_run_finds_nothing(dbs):
    # The atomic-claim guarantee: after one plan consumed the queue, an
    # immediately repeated plan (wake-coalesced duplicate session) is a no-op.
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path)
    first = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    second = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    assert len(first["orders"]) == 1 and second["orders"] == []


def test_ref_id_minted_once_and_recorded(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    ref_id = plan["orders"][0]["ref_id"]
    results = {
        "results": [
            {
                "queue_id": qid,
                "ref_id": ref_id,
                "account_number": "TESTACCT0",
                "order_id": "ord-9",
                "state": "placed",
                "raw": {},
            }
        ]
    }
    placed, errors = run.run_record(orders_path, results, "2026-07-27T13:36:00+00:00", ENV)
    assert (placed, errors) == (1, 0)
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT status FROM queue WHERE id=?", (qid,)).fetchone()[0] == "placed"
    ref, limit = conn.execute("SELECT ref_id, limit_price FROM placements").fetchone()
    assert ref == ref_id and limit == "312.62"  # limit from queue.planned_limit, not the doc


def test_record_rejects_wrong_account_or_unknown_ref_id(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    bad = {
        "results": [
            {
                "queue_id": qid,
                "ref_id": plan["orders"][0]["ref_id"],
                "account_number": "WRONG",
                "order_id": "x",
                "state": "placed",
                "raw": {},
            }
        ]
    }
    with pytest.raises(ValueError, match="account"):
        run.run_record(orders_path, bad, "t", ENV)
    bad["results"][0]["account_number"] = "TESTACCT0"
    bad["results"][0]["ref_id"] = "not-a-known-ref"
    with pytest.raises(ValueError, match="ref_id"):
        run.run_record(orders_path, bad, "t", ENV)


def test_broker_error_keeps_row_planned(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    results = {
        "results": [
            {
                "queue_id": qid,
                "ref_id": plan["orders"][0]["ref_id"],
                "account_number": "TESTACCT0",
                "order_id": None,
                "state": "error",
                "raw": {"detail": "rejected"},
            }
        ]
    }
    run.run_record(orders_path, results, "t", ENV)
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT status FROM queue WHERE id=?", (qid,)).fetchone()[0] == "planned"
    assert conn.execute("SELECT COUNT(*) FROM v_unreconciled").fetchone()[0] == 1


def test_resolve_clears_stuck_planned(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    run.run_resolve(orders_path, qid, "failed", None, "t2")
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT status FROM queue WHERE id=?", (qid,)).fetchone()[0] == "failed"
    assert conn.execute("SELECT COUNT(*) FROM v_unreconciled").fetchone()[0] == 0


def test_resolve_as_placed_writes_confirming_placement(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    run.run_resolve(orders_path, qid, "placed", "ord-manual", "t2")
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT status FROM queue WHERE id=?", (qid,)).fetchone()[0] == "placed"
    assert conn.execute("SELECT COUNT(*) FROM v_unreconciled").fetchone()[0] == 0


def test_preflight_codes(dbs):
    orders_path, cal_path = dbs
    # Empty queue -> quiet stand-down
    assert run.run_preflight(orders_path, cal_path, SUMMER_OPEN)[0] == 3
    _queue(orders_path, cal_path)
    # In window with rows -> go, prints symbols
    assert run.run_preflight(orders_path, cal_path, SUMMER_OPEN) == (0, ["TSLA"])
    # Before window / after window / weekend -> quiet stand-down
    assert run.run_preflight(orders_path, cal_path, "2026-07-27T13:31:00+00:00")[0] == 3
    assert run.run_preflight(orders_path, cal_path, "2026-07-27T20:00:00+00:00")[0] == 3
    assert run.run_preflight(orders_path, cal_path, "2026-07-26T13:35:00+00:00")[0] == 3  # Sunday


def test_preflight_holiday_stands_down(dbs, tmp_path):
    orders_path, cal_path = dbs
    conn = cal_db.connect(cal_path)
    conn.execute(
        "INSERT INTO events (event_type, event_date, subtype, title, source, fetched_at)"
        " VALUES ('market_holiday', '2026-07-27', '', 'Test holiday', 'test', 't')"
    )
    conn.commit()
    conn.close()
    _queue(orders_path, cal_path)
    assert run.run_preflight(orders_path, cal_path, SUMMER_OPEN)[0] == 3


def test_preflight_calendar_blind_is_loud(dbs, tmp_path):
    orders_path, _ = dbs
    blind_cal = str(tmp_path / "blind_cal.db")
    conn = cal_db.connect(blind_cal)
    cal_db.ensure_schema(conn)  # schema but zero holiday events
    conn.close()
    _queue(orders_path, dbs[1])
    assert run.run_preflight(orders_path, blind_cal, SUMMER_OPEN)[0] == 1


def test_plan_on_holiday_claims_nothing(dbs):
    # Python, not the wrapper, is the last line: a manually-run session on a
    # holiday inside window-clock time must not claim rows (its GFD limits
    # would queue for the NEXT open against expired intent).
    orders_path, cal_path = dbs
    conn = cal_db.connect(cal_path)
    conn.execute(
        "INSERT INTO events (event_type, event_date, subtype, title, source, fetched_at)"
        " VALUES ('market_holiday', '2026-07-27', '', 'Test holiday', 'test', 't')"
    )
    conn.commit()
    conn.close()
    _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    assert plan["orders"] == []
    oconn = orders_db.connect(orders_path)
    assert oconn.execute("SELECT status FROM queue").fetchone()[0] == "queued"


def test_queue_validation(dbs):
    orders_path, cal_path = dbs
    with pytest.raises(ValueError):  # sub-$1
        run.run_queue(
            orders_path,
            cal_path,
            "PENNY",
            10,
            0.40,
            3.0,
            "2026-07-28",
            None,
            "t",
            True,
            ENV,
        )
    _queue(orders_path, cal_path)
    with pytest.raises(ValueError, match="duplicate"):  # dup open row per symbol
        _queue(orders_path, cal_path)


def test_queue_default_expiry_refused_when_calendar_blind(dbs, tmp_path):
    orders_path, _ = dbs
    blind_cal = str(tmp_path / "blind_cal.db")
    conn = cal_db.connect(blind_cal)
    cal_db.ensure_schema(conn)
    conn.close()
    with pytest.raises(ValueError, match="calendar"):
        run.run_queue(
            orders_path,
            blind_cal,
            "TSLA",
            1,
            300.0,
            3.0,
            None,  # default expiry needs the calendar
            None,
            "2026-07-27T02:00:00+00:00",
            True,
            ENV,
        )
    # Explicit expiry is fine even when blind.
    qid = run.run_queue(
        orders_path,
        blind_cal,
        "TSLA",
        1,
        300.0,
        3.0,
        "2026-07-28",
        None,
        "2026-07-27T02:00:00+00:00",
        True,
        ENV,
    )
    assert qid >= 1


def test_queue_refuses_non_tty_without_env():
    with pytest.raises(ValueError, match="interactive"):
        run.run_queue(
            "x.db",
            "c.db",
            "TSLA",
            1,
            300.0,
            3.0,
            "2026-07-28",
            None,
            "t",
            stdin_isatty=False,
            env={},
        )


def test_reconcile_confirms_and_flags_orphans(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    ref_id = plan["orders"][0]["ref_id"]
    run.run_record(
        orders_path,
        {
            "results": [
                {
                    "queue_id": qid,
                    "ref_id": ref_id,
                    "account_number": "TESTACCT0",
                    "order_id": "ord-9",
                    "state": "placed",
                    "raw": {},
                }
            ]
        },
        "t",
        ENV,
    )
    report = run.run_reconcile(
        orders_path,
        {
            "orders": [
                {"order_id": "ord-9", "ref_id": ref_id, "symbol": "TSLA", "state": "filled"},
                {"order_id": "mystery", "ref_id": None, "symbol": "GME", "state": "filled"},
            ]
        },
        "t2",
    )
    assert report["confirmed"] == 1
    assert report["orphan_placements"] == []
    assert [o["order_id"] for o in report["orphan_orders"]] == ["mystery"]
    conn = orders_db.connect(orders_path)
    assert conn.execute("SELECT COUNT(*) FROM v_unreconciled").fetchone()[0] == 0


def test_reconcile_flags_unconfirmed_placement(dbs):
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    run.run_record(
        orders_path,
        {
            "results": [
                {
                    "queue_id": qid,
                    "ref_id": plan["orders"][0]["ref_id"],
                    "account_number": "TESTACCT0",
                    "order_id": "ord-9",
                    "state": "placed",
                    "raw": {},
                }
            ]
        },
        "t",
        ENV,
    )
    report = run.run_reconcile(orders_path, {"orders": []}, "t2")
    assert [p["order_id"] for p in report["orphan_placements"]] == ["ord-9"]


def test_gap_veto_retries_when_expiry_allows(dbs):
    # Monday gap-veto on a row expiring later in the week: the row stays
    # queued (with the retry reason recorded) and plans normally the next
    # morning once the gap closes.
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path, ref=300.0, gap=3.0, expires="2026-07-31")
    plan = run.run_plan(orders_path, cal_path, _plan_doc(ask=312.0), SUMMER_OPEN, ENV)
    assert plan["orders"] == []
    conn = orders_db.connect(orders_path)
    status, reason = conn.execute(
        "SELECT status, resolution_reason FROM queue WHERE id=?", (qid,)
    ).fetchone()
    conn.close()
    assert status == "queued" and reason.startswith("retry: gapped")
    tuesday = "2026-07-28T13:35:00+00:00"
    doc = {
        "as_of": tuesday,
        "quotes": [{"symbol": "TSLA", "ask": 305.0, "quote_ts": "2026-07-28T13:34:30+00:00"}],
        "portfolio": {"settled_cash": 9000.0},
    }
    plan2 = run.run_plan(orders_path, cal_path, doc, tuesday, ENV)
    assert [o["symbol"] for o in plan2["orders"]] == ["TSLA"]


def test_gap_down_veto_blocks_corrupt_low_ask(dbs):
    # ask far BELOW ref is a corrupt quote or news, never an auto-buy: the
    # old behavior planned a $0.01 limit and consumed the intent.
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, ref=310.0, gap=3.0)  # floor 300.70
    plan = run.run_plan(orders_path, cal_path, _plan_doc(ask=0.01), SUMMER_OPEN, ENV)
    assert plan["orders"] == []
    conn = orders_db.connect(orders_path)
    status, reason = conn.execute("SELECT status, resolution_reason FROM queue").fetchone()
    conn.close()
    assert status == "vetoed" and "gapped down" in reason


def test_queue_rejects_non_iso_expiry(dbs):
    orders_path, cal_path = dbs
    for bad in ("07/28/2026", "2026-7-4", "tomorrow"):
        with pytest.raises(ValueError, match="expires"):
            run.run_queue(
                orders_path,
                cal_path,
                "TSLA",
                1,
                300.0,
                3.0,
                bad,
                None,
                "2026-07-27T02:00:00+00:00",
                True,
                ENV,
            )


def test_plan_exception_rolls_back_cleanly(dbs, monkeypatch):
    # An exception after some rows were already claimed must erase the whole
    # transaction — claims AND the runs header — so the wrapper's freshness
    # check fires loudly instead of half the queue being silently consumed.
    import uuid as uuid_mod

    orders_path, cal_path = dbs
    _queue(orders_path, cal_path, symbol="AAA")
    _queue(orders_path, cal_path, symbol="BBB", ref=310.0)
    real = uuid_mod.uuid4
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return real()

    monkeypatch.setattr(run.uuid, "uuid4", boom)
    doc = {
        "as_of": SUMMER_OPEN,
        "quotes": [
            {"symbol": s, "ask": 312.0, "quote_ts": "2026-07-27T13:34:30+00:00"}
            for s in ("AAA", "BBB")
        ],
        "portfolio": {"settled_cash": 20000.0},
    }
    with pytest.raises(RuntimeError):
        run.run_plan(orders_path, cal_path, doc, SUMMER_OPEN, ENV)
    conn = orders_db.connect(orders_path)
    rows = conn.execute("SELECT status, ref_id FROM queue ORDER BY id").fetchall()
    n_runs = conn.execute("SELECT COUNT(*) FROM runs WHERE phase='plan'").fetchone()[0]
    conn.close()
    assert rows == [("queued", None), ("queued", None)]
    assert n_runs == 0


def test_reconcile_offplan_order_with_our_ref_is_serious(dbs):
    # Session crashed between place and record: the broker order carries a
    # ref_id we minted (it's on the queue row) but no placement exists. That
    # is 'session placed off-plan' — likely_manual must be False.
    orders_path, cal_path = dbs
    _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    ref_id = plan["orders"][0]["ref_id"]
    report = run.run_reconcile(
        orders_path,
        {"orders": [{"order_id": "ord-X", "ref_id": ref_id, "symbol": "TSLA", "state": "filled"}]},
        "t2",
    )
    (orphan,) = report["orphan_orders"]
    assert orphan["order_id"] == "ord-X" and orphan["likely_manual"] is False


def test_reconcile_error_recorded_but_broker_placed_is_surfaced(dbs):
    # A timeout recorded as state='error' while the broker actually placed:
    # the live order must surface as a SERIOUS orphan, not be suppressed.
    orders_path, cal_path = dbs
    qid = _queue(orders_path, cal_path)
    plan = run.run_plan(orders_path, cal_path, _plan_doc(), SUMMER_OPEN, ENV)
    ref_id = plan["orders"][0]["ref_id"]
    run.run_record(
        orders_path,
        {
            "results": [
                {
                    "queue_id": qid,
                    "ref_id": ref_id,
                    "account_number": "TESTACCT0",
                    "order_id": None,
                    "state": "error",
                    "raw": {"detail": "timeout"},
                }
            ]
        },
        "t",
        ENV,
    )
    report = run.run_reconcile(
        orders_path,
        {"orders": [{"order_id": "ord-Y", "ref_id": ref_id, "symbol": "TSLA", "state": "filled"}]},
        "t2",
    )
    (orphan,) = report["orphan_orders"]
    assert orphan["order_id"] == "ord-Y" and orphan["likely_manual"] is False


def test_reconcile_manual_trade_is_likely_manual(dbs):
    orders_path, cal_path = dbs
    report = run.run_reconcile(
        orders_path,
        {"orders": [{"order_id": "app-1", "ref_id": None, "symbol": "GME", "state": "filled"}]},
        "t",
    )
    (orphan,) = report["orphan_orders"]
    assert orphan["likely_manual"] is True
