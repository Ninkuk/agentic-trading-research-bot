# tests/test_finra_short_interest_db_schema.py
from sources.screeners.finra_short_interest import db


def test_ensure_schema_is_idempotent_and_creates_tables():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)            # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"securities", "short_interest", "settlements", "snapshots"} <= tables
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_latest", "v_high_days_to_cover", "v_short_interest_spikes",
            "v_symbol_history"} <= views
