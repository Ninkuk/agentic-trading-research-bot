import sqlite3

from sources.screeners.usda_screener import run as runmod

NOW = "2026-07-15T00:00:00+00:00"


def _obs(commodity, metric, value, unit="Million Bushels"):
    return {"commodity": commodity, "region": "United States", "metric": metric,
            "market_year": "2025/26", "value": value, "unit": unit,
            "report_date": "2026-06-01"}


def test_run_wasde_stores_discovered_release(tmp_path):
    db_path = str(tmp_path / "w.db")
    sid, ncommod, nobs = runmod.run_wasde(
        db_path, now_iso=NOW,
        fetch=lambda: [_obs("Corn", "ending_stocks", 2029.0),
                       _obs("Corn", "total_use", 16280.0)])
    assert nobs == 2 and ncommod == 1
    conn = sqlite3.connect(db_path)
    r = conn.execute("SELECT ROUND(stocks_to_use,3) FROM v_wasde_stocks_to_use "
                     "WHERE commodity='Corn'").fetchone()
    assert r[0] == round(2029.0 / 16280.0, 3)


def test_run_wasde_no_release_found_writes_zero(tmp_path, capsys):
    sid, ncommod, nobs = runmod.run_wasde(
        str(tmp_path / "w.db"), fetch=lambda: None, now_iso=NOW)
    assert (ncommod, nobs) == (0, 0)
    assert "warning" in capsys.readouterr().err.lower()


def test_run_wasde_fetch_error_is_nonfatal_and_hides_detail(tmp_path, capsys):
    sid, ncommod, nobs = runmod.run_wasde(
        str(tmp_path / "w.db"), now_iso=NOW,
        fetch=lambda: (_ for _ in ()).throw(RuntimeError("http://x?key=SECRET")))
    assert (ncommod, nobs) == (0, 0)
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
