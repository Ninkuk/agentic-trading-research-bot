from cftc_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _market(code="088691", name="GOLD", asset_class="metals"):
    return {"code": code, "name": name, "asset_class": asset_class}


def _cot_row(code, date, **vals):
    row = {"code": code, "report_date": date}
    row.update(vals)
    return row


def test_upsert_markets_preserves_first_seen_and_refreshes_name():
    conn = _fresh()
    db.upsert_markets(conn, [_market(name="OLD NAME")], "2026-01-01T00:00:00+00:00")
    db.upsert_markets(conn, [_market(name="NEW NAME")], "2026-07-03T00:00:00+00:00")
    first_seen, last_seen, name = conn.execute(
        "SELECT first_seen, last_seen, name FROM markets WHERE code='088691'"
    ).fetchone()
    assert first_seen == "2026-01-01T00:00:00+00:00"
    assert last_seen == "2026-07-03T00:00:00+00:00"
    assert name == "NEW NAME"


def test_write_cot_upserts_by_code_and_date():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    n1 = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-16", open_interest=100, noncomm_long=10),
        _cot_row("088691", "2026-06-23", open_interest=200, noncomm_long=20),
    ])
    assert n1 == 2
    # Revised prior week + one new week
    n2 = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-23", open_interest=250, noncomm_long=25),  # revision
        _cot_row("088691", "2026-06-30", open_interest=300, noncomm_long=30),  # new
    ])
    assert n2 == 2
    rows = conn.execute(
        "SELECT report_date, open_interest FROM cot WHERE code='088691' "
        "ORDER BY report_date").fetchall()
    assert rows == [("2026-06-16", 100), ("2026-06-23", 250), ("2026-06-30", 300)]


def test_write_cot_dedupes_within_batch_last_wins():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    n = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-23", open_interest=1),
        _cot_row("088691", "2026-06-23", open_interest=9),  # same date, later wins
    ])
    assert n == 1
    val = conn.execute(
        "SELECT open_interest FROM cot WHERE code='088691'").fetchone()[0]
    assert val == 9


def test_max_report_date_returns_none_when_empty_then_latest():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    assert db.max_report_date(conn, "088691") is None
    db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-16", open_interest=1),
        _cot_row("088691", "2026-06-23", open_interest=2),
    ])
    assert db.max_report_date(conn, "088691") == "2026-06-23"


def test_prune_deletes_old_snapshots_but_not_cot():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    db.write_cot(conn, "088691", [_cot_row("088691", "2020-01-07", open_interest=1)])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, "2026-07-01T00:00:00+00:00", 1, 1)  # recent
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 1  # preserved
