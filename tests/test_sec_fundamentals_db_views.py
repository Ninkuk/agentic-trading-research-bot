from sec_fundamentals import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_companies(conn, [{"cik": 1, "ticker": "AAA", "name": "Alpha",
                                "sic": "1"}], "t")
    return conn


def _f(tag, period_end, form, value, filed):
    return {"tag": tag, "uom": "USD", "period_end": period_end,
            "fiscal_year": int(period_end[:4]), "fiscal_period": "FY",
            "value": value, "form": form, "filed": filed, "accession": form}


def test_v_latest_fundamentals_picks_newest_period():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("Assets", "2023-12-31", "10-K", 100, "2024-02-01"),
        _f("Assets", "2024-12-31", "10-K", 150, "2025-02-01"),
    ])
    row = conn.execute("SELECT value FROM v_latest_fundamentals "
                       "WHERE tag='Assets'").fetchone()
    assert row == (150.0,)


def test_v_screener_derives_ratios():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("Revenues", "2024-12-31", "10-K", 1000, "2025-02-01"),
        _f("NetIncomeLoss", "2024-12-31", "10-K", 200, "2025-02-01"),
        _f("Liabilities", "2024-12-31", "10-K", 400, "2025-02-01"),
        _f("StockholdersEquity", "2024-12-31", "10-K", 800, "2025-02-01"),
    ])
    r = conn.execute(
        "SELECT net_margin, roe, debt_to_equity FROM v_screener "
        "WHERE cik=1").fetchone()
    assert abs(r[0] - 0.20) < 1e-9      # 200/1000
    assert abs(r[1] - 0.25) < 1e-9      # 200/800
    assert abs(r[2] - 0.50) < 1e-9      # 400/800


def test_v_screener_null_ratio_when_denominator_absent():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("NetIncomeLoss", "2024-12-31", "10-K", 200, "2025-02-01")])
    r = conn.execute("SELECT net_margin FROM v_screener WHERE cik=1").fetchone()
    assert r[0] is None                 # no Revenues -> NULL, not an error


def test_v_frame_cross_section_returns_all_filers_for_tag_period():
    conn = _seed()
    db.upsert_companies(conn, [{"cik": 2, "ticker": "BBB", "name": "Beta",
                                "sic": "1"}], "t")
    db.write_facts(conn, 1, [_f("Assets", "2024-12-31", "10-K", 10, "2025-02-01")])
    db.write_facts(conn, 2, [_f("Assets", "2024-12-31", "10-K", 20, "2025-02-01")])
    rows = conn.execute(
        "SELECT ticker, value FROM v_frame_cross_section "
        "WHERE tag='Assets' AND period_end='2024-12-31' ORDER BY value").fetchall()
    assert rows == [("AAA", 10.0), ("BBB", 20.0)]


def test_v_revisions_surfaces_restatement_with_delta():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("NetIncomeLoss", "2024-09-30", "10-Q", 90, "2024-11-01"),
        _f("NetIncomeLoss", "2024-09-30", "10-K", 100, "2025-02-01"),  # restated
    ])
    rows = conn.execute(
        "SELECT form, value, value_delta FROM v_revisions "
        "WHERE tag='NetIncomeLoss' ORDER BY filed").fetchall()
    assert rows[0] == ("10-Q", 90.0, None)         # first filing, no prior
    assert rows[1] == ("10-K", 100.0, 10.0)        # +10 restatement
