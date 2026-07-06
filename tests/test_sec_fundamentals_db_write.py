from sources.screeners.sec_fundamentals import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _co(cik, ticker="AAPL", name="APPLE INC", sic="3571"):
    return {"cik": cik, "ticker": ticker, "name": name, "sic": sic}


def _fact(tag, period_end, form, value, filed="2024-11-01", accn="a1"):
    return {
        "tag": tag,
        "uom": "USD",
        "period_end": period_end,
        "fiscal_year": 2024,
        "fiscal_period": "FY",
        "value": value,
        "form": form,
        "filed": filed,
        "accession": accn,
    }


def test_write_facts_upsert_overwrites_value_in_place():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(conn, 320193, [_fact("NetIncomeLoss", "2024-09-28", "10-Q", 90)])
    db.write_facts(conn, 320193, [_fact("NetIncomeLoss", "2024-09-28", "10-Q", 95)])
    rows = conn.execute("SELECT value FROM facts").fetchall()
    assert rows == [(95.0,)]  # revised in place, no duplicate


def test_write_facts_different_form_is_a_new_row():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(
        conn,
        320193,
        [
            _fact("NetIncomeLoss", "2024-09-28", "10-Q", 90),
            _fact("NetIncomeLoss", "2024-09-28", "10-K", 92),  # restatement
        ],
    )
    n = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    assert n == 2  # both kept -> feeds v_revisions


def test_write_facts_dedupes_within_batch_last_wins():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    n = db.write_facts(
        conn,
        320193,
        [
            _fact("Assets", "2024-09-28", "10-K", 100),
            _fact("Assets", "2024-09-28", "10-K", 200),
        ],
    )
    assert n == 1
    assert conn.execute("SELECT value FROM facts").fetchone()[0] == 200.0


def test_upsert_companies_preserves_first_seen_refreshes_label():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193, ticker="AAPL")], "t1")
    db.upsert_companies(conn, [_co(320193, ticker="APPL2")], "t2")
    row = conn.execute("SELECT ticker, first_seen, last_seen FROM companies").fetchone()
    assert row == ("APPL2", "t1", "t2")


def test_prune_deletes_old_snapshots_not_facts():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(conn, 320193, [_fact("Assets", "2024-09-28", "10-K", 100)])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)  # recent
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 1
