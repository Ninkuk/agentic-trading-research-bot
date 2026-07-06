from sources.screeners.cftc_screener import db


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
    n1 = db.write_cot(
        conn,
        "088691",
        [
            _cot_row("088691", "2026-06-16", open_interest=100, noncomm_long=10),
            _cot_row("088691", "2026-06-23", open_interest=200, noncomm_long=20),
        ],
    )
    assert n1 == 2
    # Revised prior week + one new week
    n2 = db.write_cot(
        conn,
        "088691",
        [
            _cot_row("088691", "2026-06-23", open_interest=250, noncomm_long=25),  # revision
            _cot_row("088691", "2026-06-30", open_interest=300, noncomm_long=30),  # new
        ],
    )
    assert n2 == 2
    rows = conn.execute(
        "SELECT report_date, open_interest FROM cot WHERE code='088691' ORDER BY report_date"
    ).fetchall()
    assert rows == [("2026-06-16", 100), ("2026-06-23", 250), ("2026-06-30", 300)]


def test_write_cot_dedupes_within_batch_last_wins():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    n = db.write_cot(
        conn,
        "088691",
        [
            _cot_row("088691", "2026-06-23", open_interest=1),
            _cot_row("088691", "2026-06-23", open_interest=9),  # same date, later wins
        ],
    )
    assert n == 1
    val = conn.execute("SELECT open_interest FROM cot WHERE code='088691'").fetchone()[0]
    assert val == 9


def test_max_report_date_returns_none_when_empty_then_latest():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    assert db.max_report_date(conn, "088691") is None
    db.write_cot(
        conn,
        "088691",
        [
            _cot_row("088691", "2026-06-16", open_interest=1),
            _cot_row("088691", "2026-06-23", open_interest=2),
        ],
    )
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


# --- family extension ---
from sources.screeners.cftc_screener import catalog

NOW = "2026-07-03T00:00:00+00:00"


def _seed_market(conn, code="088691"):
    db.upsert_markets(conn, [{"code": code, "name": "GOLD", "asset_class": "metals"}], NOW)


def test_write_family_derived_columns_match_table():
    # write_family derives its INSERT columns from field_map; they must all be
    # real columns of the fact table (else sqlite raises "no column named ...").
    conn = _fresh()
    for fam in (catalog.DISAGG, catalog.TFF):
        tbl_cols = {r[1] for r in conn.execute(f"PRAGMA table_info({fam.fact_table})")}
        map_cols = {c for c, _a, _cast in fam.field_map}
        assert map_cols <= tbl_cols, f"{fam.name} field_map ⊄ {fam.fact_table}"


def test_write_family_upserts_disagg_by_date():
    conn = _fresh()
    _seed_market(conn)
    n1 = db.write_family(
        conn,
        catalog.DISAGG,
        "088691",
        [
            {
                "code": "088691",
                "report_date": "2026-06-16",
                "mm_long": 10,
                "mm_short": 2,
                "open_interest": 100,
            },
            {
                "code": "088691",
                "report_date": "2026-06-23",
                "mm_long": 20,
                "mm_short": 3,
                "open_interest": 200,
            },
        ],
    )
    assert n1 == 2
    n2 = db.write_family(
        conn,
        catalog.DISAGG,
        "088691",
        [
            {
                "code": "088691",
                "report_date": "2026-06-23",
                "mm_long": 25,
                "mm_short": 3,
                "open_interest": 250,
            },  # revision
        ],
    )
    assert n2 == 1
    rows = conn.execute(
        "SELECT report_date, mm_long, open_interest FROM cot_disagg "
        "WHERE code='088691' ORDER BY report_date"
    ).fetchall()
    assert rows == [("2026-06-16", 10, 100), ("2026-06-23", 25, 250)]


def test_max_report_date_reads_family_table():
    conn = _fresh()
    _seed_market(conn)
    assert db.max_report_date(conn, "088691", "cot_disagg") is None
    db.write_family(
        conn,
        catalog.TFF,
        "088691",
        [{"code": "088691", "report_date": "2026-06-23", "lev_long": 5}],
    )
    # legacy cot is still empty for this code; family table has the row
    assert db.max_report_date(conn, "088691") is None  # 2-arg legacy
    assert db.max_report_date(conn, "088691", "cot_tff") == "2026-06-23"


def test_prune_leaves_family_tables_intact():
    conn = _fresh()
    _seed_market(conn)
    db.write_family(
        conn,
        catalog.DISAGG,
        "088691",
        [{"code": "088691", "report_date": "2020-01-07", "mm_long": 1}],
    )
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    removed = db.prune(conn, keep_days=30, now_iso=NOW)
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM cot_disagg").fetchone()[0] == 1
