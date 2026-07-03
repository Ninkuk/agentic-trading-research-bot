from cftc_screener import db


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"markets", "cot", "snapshots"} <= tables


def test_cot_has_expected_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot)")}
    assert {"code", "report_date", "open_interest", "noncomm_long",
            "noncomm_spread", "pct_oi_comm_short", "conc_net_8_short"} <= cols
