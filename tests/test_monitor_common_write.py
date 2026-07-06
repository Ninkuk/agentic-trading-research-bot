from sources.common.monitor_common import (
    connect,
    ensure_schema,
    replace_forward_window,
    upsert_events,
    write_snapshot,
)


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def _row(event_type, date, subtype="", status="scheduled", time="08:30", title="T"):
    return {
        "event_type": event_type,
        "event_date": date,
        "event_time": time,
        "subtype": subtype,
        "title": title,
        "status": status,
        "source": "fred",
        "payload": None,
    }


def test_upsert_inserts_then_firms_up_in_place():
    conn = _fresh()
    upsert_events(conn, [_row("cpi_release", "2026-08-12", "10", status="tentative")], "t1")
    upsert_events(conn, [_row("cpi_release", "2026-08-12", "10", status="confirmed")], "t2")
    rows = conn.execute("SELECT status, fetched_at FROM events").fetchall()
    assert rows == [("confirmed", "t2")]  # one row, updated in place


def test_upsert_dedupes_within_batch_last_wins():
    conn = _fresh()
    n = upsert_events(
        conn,
        [
            _row("cpi_release", "2026-08-12", "10", status="tentative"),
            _row("cpi_release", "2026-08-12", "10", status="confirmed"),
        ],
        "t",
    )
    assert n == 1
    assert conn.execute("SELECT status FROM events").fetchone()[0] == "confirmed"


def test_replace_forward_window_drops_old_future_keeps_past():
    conn = _fresh()
    upsert_events(
        conn,
        [
            _row("opex", "2026-06-19"),  # past vs today
            _row("opex", "2026-09-18"),
        ],
        "t",
    )  # stale future
    n = replace_forward_window(conn, "opex", "2026-07-03", [_row("opex", "2026-08-21")], "t2")
    assert n == 1
    dates = [r[0] for r in conn.execute("SELECT event_date FROM events ORDER BY event_date")]
    assert dates == ["2026-06-19", "2026-08-21"]  # past kept, old future gone


def test_write_snapshot_returns_id_and_stores_source_and_count():
    conn = _fresh()
    sid = write_snapshot(conn, "2026-07-03T00:00:00+00:00", 7, "fred")
    got = conn.execute("SELECT event_count, source FROM snapshots WHERE id=?", (sid,)).fetchone()
    assert got == (7, "fred")
