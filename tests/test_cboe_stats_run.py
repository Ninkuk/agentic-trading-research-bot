import sqlite3

from sources.screeners.cboe_stats import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _pcr(d):
    return [{"date": d, "total_pcr": 0.9, "equity_pcr": 0.7, "index_pcr": None,
             "total_volume": None}]


def _vix(d, close):
    return [{"date": d, "open": None, "high": None, "low": None, "close": close}]


def test_run_default_fetches_pcr_feed(tmp_path):
    called = {"pcr": False}

    def fpcr():
        called["pcr"] = True
        return _pcr("2026-06-01")

    # no `only` -> default enabled feeds, which include PCR again
    runmod.run(str(tmp_path / "c.db"), fetch_pcr=fpcr,
               fetch_vix=lambda fid: _vix("2026-06-01", 14.6), now_iso=NOW)
    assert called["pcr"] is True


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "c.db")
    sid, fc, rc = runmod.run(
        db_path, only=["PCR", "VIX", "VIX3M"],
        fetch_pcr=lambda: _pcr("2026-06-01"),
        fetch_vix=lambda fid: _vix("2026-06-01", 14.6 if fid == "VIX" else 16.0),
        now_iso=NOW)
    assert fc == 3 and rc == 3
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT close, vix3m FROM vix_daily").fetchone() == (14.6, 16.0)


def test_run_skips_failing_feed_hides_secret(tmp_path, capsys):
    def fetch_vix(fid):
        if fid == "VIX":
            raise RuntimeError("https://cdn.cboe.com?k=SECRET boom")
        return _vix("2026-06-01", 16.0)

    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["VIX", "VIX3M"],
                             fetch_vix=fetch_vix, now_iso=NOW)
    assert fc == 1                                 # VIX failed, VIX3M stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_none_feed_skipped(tmp_path):
    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["VIX"],
                             fetch_vix=lambda fid: None, now_iso=NOW)
    assert fc == 0 and rc == 0                      # 403/404 -> None -> skip


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["PCR"],
                             fetch_pcr=lambda: (_ for _ in ()).throw(RuntimeError("x")),
                             now_iso=NOW)
    assert (fc, rc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "c.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "c.db")
    runmod.run(db_path, only=["PCR"], fetch_pcr=lambda: _pcr("2026-06-01"),
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["PCR"], fetch_pcr=lambda: _pcr("2026-06-01"),
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM pcr_daily").fetchone()[0] == 1
