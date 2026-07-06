from sources.screeners.fred_screener import db
from sources.screeners.fred_screener import run as run_mod
from sources.screeners.fred_screener.catalog import Series


def _theme_lookup(series_id):
    return "rates"


def _ok_series(series_id, api_key, get=None):
    return {"id": series_id, "title": f"title-{series_id}", "frequency": "Monthly"}


def _ok_obs(series_id, api_key, start=None, get=None):
    return [{"date": "2026-01-01", "value": 1.0}, {"date": "2026-02-01", "value": 2.0}]


NOW = "2026-07-02T00:00:00+00:00"


def test_run_happy_path_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("A", "rates"), Series("B", "growth")])
    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(
        dbp, api_key="K", now_iso=NOW, fetch_series=_ok_series, fetch_obs=_ok_obs
    )
    assert sc == 2
    assert oc == 4  # 2 series * 2 obs
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 2


def test_run_skips_failing_series_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        run_mod.catalog, "CATALOG", [Series("GOOD", "rates"), Series("BAD", "rates")]
    )

    def flaky_series(series_id, api_key, get=None):
        if series_id == "BAD":
            raise RuntimeError("boom")
        return _ok_series(series_id, api_key)

    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(
        dbp, api_key="K", now_iso=NOW, fetch_series=flaky_series, fetch_obs=_ok_obs
    )
    assert sc == 1  # only GOOD stored
    assert "BAD" in capsys.readouterr().err
    conn = db.connect(dbp)
    ids = [r[0] for r in conn.execute("SELECT series_id FROM series")]
    assert ids == ["GOOD"]


def test_run_all_fail_writes_zero_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("BAD", "rates")])

    def boom(series_id, api_key, get=None):
        raise RuntimeError("nope")

    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(dbp, api_key="K", now_iso=NOW, fetch_series=boom, fetch_obs=_ok_obs)
    assert (sc, oc) == (0, 0)
    conn = db.connect(dbp)
    snap = conn.execute("SELECT series_count, observation_count FROM snapshots").fetchone()
    assert snap == (0, 0)


def test_run_only_selects_subset(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("A", "rates"), Series("B", "rates")])
    dbp = str(tmp_path / "fred.db")
    _, sc, _ = run_mod.run(
        dbp, only=["B"], api_key="K", now_iso=NOW, fetch_series=_ok_series, fetch_obs=_ok_obs
    )
    assert sc == 1
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT series_id FROM series")] == ["B"]


def test_run_second_run_upserts_revised_value(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("A", "rates")])
    dbp = str(tmp_path / "fred.db")

    def obs_v1(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    def obs_v2(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.5}]  # revised

    run_mod.run(dbp, api_key="K", now_iso=NOW, fetch_series=_ok_series, fetch_obs=obs_v1)
    run_mod.run(dbp, api_key="K", now_iso=NOW, fetch_series=_ok_series, fetch_obs=obs_v2)

    conn = db.connect(dbp)
    rows = conn.execute("SELECT value FROM observations WHERE series_id='A'").fetchall()
    assert rows == [(1.5,)]  # single row, revised in place


def test_run_skips_failing_write_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        run_mod.catalog, "CATALOG", [Series("GOOD", "rates"), Series("BADW", "rates")]
    )
    orig_write = run_mod.db.write_observations

    def flaky_write(conn, series_id, obs_rows):
        if series_id == "BADW":
            raise RuntimeError("disk full")
        return orig_write(conn, series_id, obs_rows)

    monkeypatch.setattr(run_mod.db, "write_observations", flaky_write)
    dbp = str(tmp_path / "fred.db")
    _, sc, _ = run_mod.run(
        dbp, api_key="K", now_iso=NOW, fetch_series=_ok_series, fetch_obs=_ok_obs
    )
    assert sc == 1  # only GOOD counted
    assert "BADW" in capsys.readouterr().err
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT DISTINCT series_id FROM observations")] == [
        "GOOD"
    ]  # BADW rolled back


def test_run_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with __import__("pytest").raises(RuntimeError) as exc:
        run_mod.run(
            str(tmp_path / "x.db"),
            api_key=None,
            now_iso=NOW,
            fetch_series=_ok_series,
            fetch_obs=_ok_obs,
        )
    assert "FRED_API_KEY" in str(exc.value)
