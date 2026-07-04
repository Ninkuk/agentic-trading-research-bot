from econ_calendar import db
from econ_calendar.catalog import CATALOG


def test_ensure_schema_creates_events_snapshots_catalog_and_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "release_catalog"} <= tables
    assert {"v_upcoming_releases", "v_imminent_high_impact",
            "v_this_week"} <= views


def test_ensure_schema_idempotent_and_syncs_full_catalog():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise or duplicate rows
    n = conn.execute("SELECT COUNT(*) FROM release_catalog").fetchone()[0]
    assert n == len(CATALOG)
