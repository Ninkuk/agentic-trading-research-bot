from sources.screeners.sec_fundamentals import db


def test_ensure_schema_creates_tables_and_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"companies", "facts", "snapshots"} <= tables


def test_facts_primary_key_includes_form():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(facts)")]
    assert {"cik", "tag", "period_end", "form", "value", "filed", "accession"} <= set(cols)
