# tests/test_cftc_run.py
from cftc_screener import db, run as run_mod
from cftc_screener.catalog import Market

NOW = "2026-07-03T00:00:00+00:00"


def _rows(code, series):
    """series: list of (date, noncomm_long). Newest last (fetch orders ascending)."""
    return [{"code": code, "report_date": d, "name": f"name-{code}",
             "noncomm_long": lo, "noncomm_short": 0, "open_interest": 1000}
            for (d, lo) in series]


def test_run_happy_path_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("A", "Alpha", "metals"),
                         Market("B", "Beta", "energy")])

    def fake_fetch(code, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-16", 10), ("2026-06-23", 20)])

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)
    assert mc == 2
    assert rc == 4  # 2 markets * 2 weeks
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0] == 2
    # market name comes from the newest fetched row
    assert conn.execute("SELECT name FROM markets WHERE code='A'").fetchone()[0] == "name-A"


def test_run_skips_failing_market_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("GOOD", "G", "metals"),
                         Market("BAD", "B", "metals")])

    def flaky(code, app_token=None, since=None, start=None):
        if code == "BAD":
            raise RuntimeError("boom")
        return _rows(code, [("2026-06-23", 5)])

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=flaky)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["GOOD"]
    assert "BAD" in capsys.readouterr().err


def test_run_passes_since_from_max_stored_date(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, app_token=None, since=None, start=None):
        seen.setdefault("since", []).append(since)
        return _rows(code, [("2026-06-16", 1), ("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # since=None (empty db)
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # since=latest stored
    assert seen["since"] == [None, "2026-06-23"]


def test_run_all_fail_writes_zero_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("BAD", "B", "metals")])

    def boom(code, app_token=None, since=None, start=None):
        raise RuntimeError("nope")

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=boom)
    assert (mc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT market_count, row_count FROM snapshots").fetchone() == (0, 0)


def test_run_only_selects_subset(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("A", "Alpha", "metals"),
                         Market("B", "Beta", "metals")])

    def fake_fetch(code, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 1)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, only=["B"], now_iso=NOW, fetch_rows=fake_fetch)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["B"]
