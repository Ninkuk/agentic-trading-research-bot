import sqlite3

from sources.screeners.eia_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"
CATALOG_ID = "WCESTUS1"


def _obs(*periods):
    return ([{"period": p, "value": v} for p, v in periods], "MBBL")


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_series_obs(route, facet, api_key, start=None):
        return _obs(("2026-06-26", 415.0), ("2026-06-19", 420.0))

    sid, sc, oc = runmod.run(
        db_path, only=[CATALOG_ID], api_key="K", fetch_series_obs=fetch_series_obs, now_iso=NOW
    )
    assert sc == 1 and oc == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT unit FROM series").fetchone()[0] == "MBBL"


def test_run_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    try:
        runmod.run(str(tmp_path / "e.db"), now_iso=NOW)
        assert False, "expected RuntimeError for missing key"
    except RuntimeError as e:
        assert "EIA_API_KEY" in str(e)


def test_run_skips_failing_series_hides_key(tmp_path, capsys):
    def fetch_series_obs(route, facet, api_key, start=None):
        if facet == "WCESTUS1":
            raise RuntimeError("https://api.eia.gov?api_key=SECRETKEY boom")
        return _obs(("2026-06-26", 1.0))

    sid, sc, oc = runmod.run(
        str(tmp_path / "e.db"),
        only=["WCESTUS1", "WGTSTUS1"],
        api_key="K",
        fetch_series_obs=fetch_series_obs,
        now_iso=NOW,
    )
    assert sc == 1  # first failed, second stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "SECRETKEY" not in err  # key/message never leaked


def test_run_add_route_facet_token(tmp_path):
    seen = []

    def fetch_series_obs(route, facet, api_key, start=None):
        seen.append((route, facet))
        return _obs(("2026-06-26", 1.0))

    runmod.run(
        str(tmp_path / "e.db"),
        only=[],
        add=["natural-gas/stor/wkly:F1"],
        api_key="K",
        fetch_series_obs=fetch_series_obs,
        now_iso=NOW,
    )
    assert ("natural-gas/stor/wkly", "F1") in seen
    conn = sqlite3.connect(str(tmp_path / "e.db"))
    assert (
        conn.execute("SELECT category FROM series WHERE series_id='F1'").fetchone()[0] == "custom"
    )


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(route, facet, api_key, start=None):
        raise RuntimeError("x")

    sid, sc, oc = runmod.run(
        str(tmp_path / "e.db"), only=["WCESTUS1"], api_key="K", fetch_series_obs=boom, now_iso=NOW
    )
    assert (sc, oc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "e.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_obs(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_series_obs(route, facet, api_key, start=None):
        return _obs(("2026-06-26", 1.0))

    runmod.run(
        db_path,
        only=["WCESTUS1"],
        api_key="K",
        fetch_series_obs=fetch_series_obs,
        now_iso="2026-01-01T00:00:00+00:00",
    )
    runmod.run(
        db_path,
        only=["WCESTUS1"],
        api_key="K",
        fetch_series_obs=fetch_series_obs,
        now_iso=NOW,
        keep_days=30,
    )
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM eia_obs").fetchone()[0] == 1
