from pipeline.leads import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_tables_and_views_exist():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"snapshots", "source_state", "leads", "regime",
            "v_latest_leads", "v_leads_by_instrument"} <= names


def test_ensure_schema_is_idempotent():
    conn = _fresh()
    db.ensure_schema(conn)  # second call must not raise


def test_leads_primary_key_is_snapshot_instrument_signal():
    conn = _fresh()
    cols = {r[1]: r[5] for r in conn.execute("PRAGMA table_info(leads)")}
    assert cols["snapshot_id"] > 0
    assert cols["instrument"] > 0
    assert cols["signal"] > 0
    assert cols["score"] == 0
