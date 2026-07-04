import sources.common.monitor_common as monitor_common
from econ_calendar import db
from econ_calendar.catalog import CATALOG

CPI = next(r for r in CATALOG if r.event_type == "cpi_release")
MED = next(r for r in CATALOG if r.impact == "med")  # JOLTS — exercises exclusion


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _evt(event_type, date, subtype, status="scheduled"):
    return {"event_type": event_type, "event_date": date, "event_time": "08:30",
            "subtype": subtype, "title": "T", "status": status,
            "source": "fred", "payload": None}


def test_upsert_firms_up_no_duplicate():
    conn = _fresh()
    sub = str(CPI.release_id)
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", sub, "tentative")], "t1")
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", sub, "confirmed")], "t2")
    assert conn.execute("SELECT status FROM events").fetchall() == [("confirmed",)]


def test_v_imminent_high_impact_filters_high_within_horizon():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00", horizon_days=14)
    sub = str(CPI.release_id)
    monitor_common.upsert_events(conn, [
        _evt("cpi_release", "2026-08-12", sub),   # high, 11 days out -> in
        _evt("cpi_release", "2026-09-30", sub),   # high, outside horizon -> out
    ], "t")
    got = [r[0] for r in conn.execute(
        "SELECT event_date FROM v_imminent_high_impact")]
    assert got == ["2026-08-12"]


def test_v_imminent_high_impact_excludes_med_impact_release():
    # With a med-impact release in the catalog (JOLTS), prove the impact='high'
    # filter actually drops a med row that is otherwise inside the horizon.
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00", horizon_days=14)
    monitor_common.upsert_events(conn, [
        _evt("cpi_release", "2026-08-12", str(CPI.release_id)),   # high -> in
        _evt(MED.event_type, "2026-08-10", str(MED.release_id)),  # med -> excluded
    ], "t")
    got = [r[0] for r in conn.execute(
        "SELECT event_type FROM v_imminent_high_impact")]
    assert got == ["cpi_release"]              # med release filtered out


def test_v_upcoming_releases_joins_catalog_impact_and_label():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00")
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", str(CPI.release_id))], "t")
    row = conn.execute(
        "SELECT event_type, impact, label FROM v_upcoming_releases").fetchone()
    assert row == ("cpi_release", CPI.impact, CPI.label)
