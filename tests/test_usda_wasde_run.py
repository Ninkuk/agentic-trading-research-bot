import sqlite3

from usda_screener import run as runmod

NOW = "2026-07-15T00:00:00+00:00"    # current release month: 2026-07


def _obs(commodity, metric, value, unit="Million Bushels"):
    return {"commodity": commodity, "region": "United States", "metric": metric,
            "market_year": "2025/26", "value": value, "unit": unit,
            "report_date": "2026-06-11"}


def test_run_wasde_walks_back_to_latest_published_release(tmp_path):
    db_path = str(tmp_path / "w.db")
    calls = []

    def fetch(year, month):
        calls.append((year, month))
        if (year, month) == (2026, 6):           # the newest published release
            return [_obs("Corn", "ending_stocks", 2029.0),
                    _obs("Corn", "total_use", 16280.0)]
        return None                              # 2026-07 not published yet

    sid, ncommod, nobs = runmod.run_wasde(db_path, fetch=fetch, now_iso=NOW)
    assert calls[0] == (2026, 7)                 # tries current month first
    assert (2026, 6) in calls                    # then walks back
    assert nobs == 2 and ncommod == 1
    conn = sqlite3.connect(db_path)
    r = conn.execute("SELECT ROUND(stocks_to_use,3) FROM v_wasde_stocks_to_use "
                     "WHERE commodity='Corn'").fetchone()
    assert r[0] == round(2029.0 / 16280.0, 3)


def test_run_wasde_no_release_found_writes_zero(tmp_path, capsys):
    sid, ncommod, nobs = runmod.run_wasde(
        str(tmp_path / "w.db"), fetch=lambda y, m: None, now_iso=NOW)
    assert (ncommod, nobs) == (0, 0)
    assert "warning" in capsys.readouterr().err.lower()


def test_run_wasde_explicit_month(tmp_path):
    calls = []

    def fetch(year, month):
        calls.append((year, month))
        return [_obs("Wheat", "ending_stocks", 901.0)]

    runmod.run_wasde(str(tmp_path / "w.db"), year=2025, month=12, fetch=fetch,
                     now_iso=NOW)
    assert calls == [(2025, 12)]                 # no walk-back when pinned
