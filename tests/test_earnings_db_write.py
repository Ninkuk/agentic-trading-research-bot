import json

from earnings_calendar import run as runmod

NOW = "2026-07-06T00:00:00+00:00"


def _row(ticker, date, timing="amc", name="X"):
    return {"ticker": ticker, "name": name, "date": date, "timing": timing,
            "eps_est": 1.0, "eps_growth": None, "rev_est": 2.0, "rev_growth": None,
            "mktcap": 5e9}


def test_build_events_maps_subtype_time_and_payload():
    ev = runmod.build_events([_row("AAPL", "2026-07-08", "bmo")], NOW)[0]
    assert ev["event_type"] == "earnings" and ev["subtype"] == "AAPL"
    assert ev["event_date"] == "2026-07-08"
    assert ev["event_time"] == "before open"
    assert ev["status"] == "scheduled" and ev["source"] == "stockanalysis"
    assert json.loads(ev["payload"])["eps_est"] == 1.0


def test_run_shifted_date_updates_in_place_no_duplicate(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("AAPL", "2026-07-08")],
               now_iso=NOW)
    runmod.run(db_path, fetch_forward=lambda: [_row("AAPL", "2026-07-09")],
               now_iso=NOW)                       # date moved
    conn = sqlite3.connect(db_path)
    dates = [r[0] for r in conn.execute(
        "SELECT event_date FROM events WHERE subtype='AAPL'")]
    assert dates == ["2026-07-09"]                # old future date replaced


def test_run_edgar_confirm_flips_status_and_source(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "e.db")

    def confirm(tickers, scheduled_by_ticker, **kw):
        return {("AAPL", "2026-07-08")}

    runmod.run(db_path, only=["AAPL"],
               fetch_forward=lambda: [_row("AAPL", "2026-07-08")],
               confirm=confirm, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status, source FROM events WHERE subtype='AAPL'").fetchone()
    assert row == ("confirmed", "edgar")
