from sources.common.monitor_common import (
    connect,
    ensure_schema,
    prune,
    set_today,
    upsert_events,
    write_snapshot,
)


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def _row(date):
    return {
        "event_type": "a",
        "event_date": date,
        "event_time": "08:30",
        "subtype": "",
        "title": "T",
        "status": "scheduled",
        "source": "fred",
        "payload": None,
    }


def test_v_upcoming_includes_today_excludes_past():
    conn = _fresh()
    set_today(conn, "2026-07-03T12:00:00+00:00")
    upsert_events(conn, [_row("2026-06-01"), _row("2026-07-03"), _row("2026-08-01")], "t")
    dates = [r[0] for r in conn.execute("SELECT event_date FROM v_upcoming")]
    assert dates == ["2026-07-03", "2026-08-01"]


def test_v_imminent_respects_horizon_boundary():
    conn = _fresh()
    set_today(conn, "2026-07-03T12:00:00+00:00", horizon_days=7)
    upsert_events(
        conn,
        [
            _row("2026-07-05"),  # 2 days out -> in
            _row("2026-07-10"),  # 7 days out -> in (inclusive)
            _row("2026-07-20"),
        ],
        "t",
    )  # 17 days out -> out
    dates = [r[0] for r in conn.execute("SELECT event_date FROM v_imminent")]
    assert dates == ["2026-07-05", "2026-07-10"]


def test_prune_deletes_old_snapshots_but_never_events():
    conn = _fresh()
    set_today(conn, "2026-07-03T12:00:00+00:00")
    upsert_events(conn, [_row("2026-12-31")], "t")  # far-future event
    write_snapshot(conn, "2026-01-01T12:00:00+00:00", 1, "fred")  # old header
    write_snapshot(conn, "2026-07-03T12:00:00+00:00", 1, "fred")  # recent header
    removed = prune(conn, keep_days=30, now_iso="2026-07-03T12:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_set_today_uses_the_phoenix_date_after_the_utc_rollover():
    """A monitor run after 17:00 Phoenix must still call today "today".

    set_today derived the date from the UTC instant, so a run late enough to
    have crossed 00:00 UTC recorded tomorrow — which would drop today's events
    out of v_upcoming and stop replace_forward_window from re-deleting them.
    The morning slots hid this; nothing in the schedule enforced it.
    """
    conn = _fresh()
    # 21:00 Phoenix on 2026-07-03 == 04:00 UTC on 2026-07-04.
    assert set_today(conn, "2026-07-04T04:00:00+00:00") == "2026-07-03"
    upsert_events(conn, [_row("2026-07-03"), _row("2026-07-04")], "t")
    dates = [r[0] for r in conn.execute("SELECT event_date FROM v_upcoming")]
    assert dates == ["2026-07-03", "2026-07-04"]  # today is not yet past
