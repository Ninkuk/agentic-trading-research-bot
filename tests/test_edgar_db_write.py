from edgar_screener.db import (connect, ensure_schema, prune, upsert_issuers,
                               write_snapshot)


def _rows():
    return [
        {"accession": "0001-25-001", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "4", "bucket": "insider",
         "filed_date": "2025-06-02", "path": "edgar/data/1000623/0001-25-001.txt"},
        {"accession": "0002-25-002", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "4", "bucket": "insider",
         "filed_date": "2025-06-02", "path": "edgar/data/1000623/0002-25-002.txt"},
        {"accession": "0003-25-003", "cik": 999999, "company": "Private Co",
         "ticker": None, "form": "D", "bucket": "other",
         "filed_date": "2025-06-02", "path": "edgar/data/999999/0003-25-003.txt"},
    ]


def test_write_snapshot_stores_rows_and_count():
    conn = connect(":memory:")
    ensure_schema(conn)
    sid, n = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    assert n == 3
    assert conn.execute(
        "SELECT filing_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM filings WHERE snapshot_id=? AND cik=1000623",
        (sid,)).fetchone()[0] == 2


def test_v_insider_activity_counts_clusters():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    row = conn.execute(
        "SELECT insider_filings FROM v_insider_activity WHERE ticker='MATV'").fetchone()
    assert row[0] == 2


def test_v_tickered_excludes_untickered():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    tickers = {r[0] for r in conn.execute("SELECT ticker FROM v_tickered").fetchall()}
    assert tickers == {"MATV"}   # None-ticker 'D' filing excluded


def test_upsert_issuers_preserves_first_seen():
    conn = connect(":memory:")
    ensure_schema(conn)
    upsert_issuers(conn, _rows(), "2026-07-01T00:00:00+00:00")
    upsert_issuers(conn, _rows(), "2026-07-02T00:00:00+00:00")
    row = conn.execute(
        "SELECT ticker, first_seen, last_seen FROM issuers WHERE cik=1000623").fetchone()
    assert row == ("MATV", "2026-07-01T00:00:00+00:00", "2026-07-02T00:00:00+00:00")


def test_v_activity_history_deltas():
    conn = connect(":memory:")
    ensure_schema(conn)
    # day 1: MATV has 2 insider filings
    write_snapshot(conn, "2026-07-01T00:00:00+00:00", "2025-06-02", _rows())
    # day 2: MATV has 1 filing
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-03", [
        {"accession": "0009-25-009", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "8-K", "bucket": "event",
         "filed_date": "2025-06-03", "path": "edgar/data/1000623/0009-25-009.txt"}])
    delta = conn.execute(
        "SELECT filings_delta_since_last FROM v_activity_history "
        "WHERE ticker='MATV' AND index_date='2025-06-03'").fetchone()[0]
    assert delta == -1   # 1 - 2


def test_prune_removes_old_snapshots_and_filings():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-06-01T00:00:00+00:00", "2025-06-01", _rows())
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM filings").fetchone()[0] == 3
