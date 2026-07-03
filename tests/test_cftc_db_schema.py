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


# --- family extension ---
def test_family_tables_and_legacy_coexist():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"markets", "cot", "cot_disagg", "cot_tff", "snapshots"} <= tables


def test_cot_disagg_has_managed_money_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot_disagg)")}
    assert {"code", "report_date", "open_interest",
            "mm_long", "mm_short", "mm_spread", "swap_spread",
            "pct_oi_mm_long", "chg_mm_long"} <= cols


def test_cot_tff_has_leveraged_funds_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot_tff)")}
    assert {"code", "report_date", "open_interest",
            "lev_long", "lev_short", "lev_spread", "dealer_spread",
            "pct_oi_lev_long", "chg_lev_long"} <= cols


def test_family_views_exist():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_disagg_net", "v_disagg_cot_index_latest", "v_disagg_positioning",
            "v_managed_money_extremes", "v_tff_net", "v_tff_cot_index_latest",
            "v_leveraged_funds_positioning", "v_leveraged_funds_extremes"} <= views
