import sqlite3

from sources.screeners.usda_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _rows(*pairs):
    return [{"period": p, "value": v, "unit": "BU"} for p, v in pairs]


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "u.db")

    def fetch_target(query, api_key):
        return _rows(("2025", 2000.0), ("2024", 1900.0))

    sid, sc, oc = runmod.run(
        db_path, only=["CORN:ENDING_STOCKS"], api_key="K", fetch_target=fetch_target, now_iso=NOW
    )
    assert sc == 1 and oc == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 2


def test_run_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NASS_API_KEY", raising=False)
    try:
        runmod.run(str(tmp_path / "u.db"), now_iso=NOW)
        assert False, "expected RuntimeError for missing key"
    except RuntimeError as e:
        assert "NASS_API_KEY" in str(e)


def test_run_skips_failing_target_hides_key(tmp_path, capsys):
    def fetch_target(query, api_key):
        if query["commodity_desc"] == "CORN":
            raise RuntimeError("https://quickstats?key=SECRETKEY boom")
        return _rows(("2025", 1.0))

    sid, sc, oc = runmod.run(
        str(tmp_path / "u.db"),
        only=["CORN:ENDING_STOCKS", "SOYBEANS:ENDING_STOCKS"],
        api_key="K",
        fetch_target=fetch_target,
        now_iso=NOW,
    )
    assert sc == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRETKEY" not in err


def test_run_add_known_pair(tmp_path):
    seen = []

    def fetch_target(query, api_key):
        seen.append(query["commodity_desc"])
        return _rows(("2025", 1.0))

    runmod.run(
        str(tmp_path / "u.db"),
        only=[],
        add=["WHEAT:PRODUCTION"],
        api_key="K",
        fetch_target=fetch_target,
        now_iso=NOW,
    )
    assert "WHEAT" in seen


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(query, api_key):
        raise RuntimeError("x")

    sid, sc, oc = runmod.run(
        str(tmp_path / "u.db"),
        only=["CORN:PRODUCTION"],
        api_key="K",
        fetch_target=boom,
        now_iso=NOW,
    )
    assert (sc, oc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "u.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_obs(tmp_path):
    db_path = str(tmp_path / "u.db")

    def fetch_target(query, api_key):
        return _rows(("2025", 1.0))

    runmod.run(
        db_path,
        only=["CORN:PRODUCTION"],
        api_key="K",
        fetch_target=fetch_target,
        now_iso="2026-01-01T00:00:00+00:00",
    )
    runmod.run(
        db_path,
        only=["CORN:PRODUCTION"],
        api_key="K",
        fetch_target=fetch_target,
        now_iso=NOW,
        keep_days=30,
    )
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 1
