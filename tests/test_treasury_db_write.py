from sources.screeners.treasury_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_dts_cash_upsert_in_place():
    conn = _fresh()
    row = {"record_date": "2026-01-02", "account_type": "TGA",
           "open_balance": 700.0, "close_balance": 750.0}
    db.write_dts_cash(conn, [row])
    db.write_dts_cash(conn, [{**row, "close_balance": 800.0}])   # restated
    got = conn.execute("SELECT close_balance FROM dts_cash").fetchall()
    assert got == [(800.0,)]                     # updated in place, no duplicate


def test_write_dedupes_within_batch_last_wins():
    conn = _fresh()
    n = db.write_debt_penny(conn, [
        {"record_date": "2026-01-02", "tot_pub_debt_out": 1.0,
         "debt_held_public": None, "intragov_hold": None},
        {"record_date": "2026-01-02", "tot_pub_debt_out": 2.0,
         "debt_held_public": None, "intragov_hold": None},
    ])
    assert n == 1
    assert conn.execute("SELECT tot_pub_debt_out FROM debt_penny").fetchone()[0] == 2.0


def test_write_yield_curve_and_auctions_persist_null_blank():
    conn = _fresh()
    db.write_yield_curve(conn, [{"record_date": "2026-01-02", "mo1": 4.5,
        "mo2": None, "mo3": 4.3, "mo4": None, "mo6": None, "yr1": None,
        "yr2": 3.8, "yr3": None, "yr5": None, "yr7": None, "yr10": 3.9,
        "yr20": None, "yr30": None}])
    assert conn.execute("SELECT yr10, mo2 FROM yield_curve").fetchone() == (3.9, None)
    db.write_upcoming_auctions(conn, [{"cusip": None, "security_type": "Note",
        "security_term": "10-Year", "announcement_date": "2026-01-05",
        "auction_date": "2026-01-12", "issue_date": "2026-01-15"}])
    assert conn.execute("SELECT auction_date FROM upcoming_auctions").fetchone()[0] \
        == "2026-01-12"


def test_prune_deletes_old_snapshots_not_facts():
    conn = _fresh()
    db.write_debt_penny(conn, [{"record_date": "2026-01-02", "tot_pub_debt_out": 1.0,
        "debt_held_public": None, "intragov_hold": None}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1
