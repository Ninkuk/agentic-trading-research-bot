import json

from sources.screeners.fred_screener import db, fetch
from sources.screeners.fred_screener import run as run_mod
from sources.screeners.fred_screener.catalog import Series


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_vintage_upsert_and_pk():
    conn = _fresh()
    n = db.write_observation_vintages(
        conn,
        "CPIAUCSL",
        [
            {"date": "2026-05-01", "realtime_start": "2026-06-10", "value": 320.0},
            {"date": "2026-05-01", "realtime_start": "2026-07-11", "value": 321.5},
            {"date": "2026-05-01", "realtime_start": "2026-06-10", "value": 320.1},
        ],
    )
    assert n == 2  # third row dedupes onto the first (last wins)
    rows = conn.execute(
        "SELECT realtime_start, value FROM observation_vintages "
        "WHERE series_id='CPIAUCSL' ORDER BY realtime_start"
    ).fetchall()
    assert rows == [("2026-06-10", 320.1), ("2026-07-11", 321.5)]


def test_v_asof_returns_value_as_known_on_date():
    conn = _fresh()
    db.write_observation_vintages(
        conn,
        "CPIAUCSL",
        [
            {"date": "2026-05-01", "realtime_start": "2026-06-10", "value": 320.0},
            {"date": "2026-05-01", "realtime_start": "2026-07-11", "value": 321.5},
        ],
    )
    db.set_asof(conn, "2026-06-15")  # revision of 07-11 not yet published
    row = conn.execute(
        "SELECT value, realtime_start FROM v_asof WHERE series_id='CPIAUCSL' AND date='2026-05-01'"
    ).fetchone()
    assert row == (320.0, "2026-06-10")
    db.set_asof(conn, "2026-07-15T09:00:00+00:00")  # full isoformat accepted
    row = conn.execute("SELECT value FROM v_asof WHERE series_id='CPIAUCSL'").fetchone()
    assert row == (321.5,)


def test_v_asof_hides_not_yet_published():
    conn = _fresh()
    db.write_observation_vintages(
        conn, "UNRATE", [{"date": "2026-06-01", "realtime_start": "2026-07-02", "value": 4.1}]
    )
    db.set_asof(conn, "2026-07-01")
    assert conn.execute("SELECT COUNT(*) FROM v_asof WHERE series_id='UNRATE'").fetchone()[0] == 0


def _qs(url):
    import urllib.parse

    return dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))


def test_fetch_vintage_dates_paginates_and_sorts():
    calls = []

    def fake_get(url):
        assert "series/vintagedates" in url
        off = int(_qs(url)["offset"])
        calls.append(off)
        alld = ["2020-03-01", "2020-01-01", "2020-02-01", "2020-04-01"]  # unsorted
        return json.dumps({"vintage_dates": alld[off : off + 2]})

    out = fetch.fetch_vintage_dates("X", "K", get=fake_get, page=2)
    assert out == ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"]
    assert calls == [0, 2, 4]  # two full pages then an empty short page -> stop


def test_fetch_observation_vintages_windows_paginates_and_dedups():
    # 3 vintage dates, window_max=2 -> windows [d0,d1] and [d2]; page_limit=1
    # forces offset pagination inside window 1.
    vds = ["2020-01-01", "2020-02-01", "2020-03-01"]

    def fake_vdates(series_id, api_key, get=None, page=None):
        return vds

    obs_calls = []

    def fake_get(url):
        assert "series/observations" in url
        q = _qs(url)
        rt0, rt1, off = q["realtime_start"], q["realtime_end"], int(q["offset"])
        obs_calls.append((rt0, rt1, off))
        if (rt0, rt1) == ("2020-01-01", "2020-02-01"):
            data = [
                {"date": "d", "realtime_start": "2020-01-01", "value": "1"},
                {"date": "d", "realtime_start": "2020-02-01", "value": "2"},
            ]
        else:
            # window 2 returns a CLAMPED restatement of the value current at its edge
            data = [{"date": "d", "realtime_start": "2020-03-01", "value": "2"}]
        return json.dumps({"observations": data[off : off + 1]})

    rows = fetch.fetch_observation_vintages(
        "X", "K", get=fake_get, get_vintage_dates=fake_vdates, window_max=2, page_limit=1
    )
    assert sorted((r["date"], r["realtime_start"], r["value"]) for r in rows) == [
        ("d", "2020-01-01", 1.0),
        ("d", "2020-02-01", 2.0),
        ("d", "2020-03-01", 2.0),
    ]
    # window 1 offset-paginated (0, 1, then short page at 2 stops it)
    assert ("2020-01-01", "2020-02-01", 0) in obs_calls
    assert ("2020-01-01", "2020-02-01", 1) in obs_calls
    # window 2 realtime bounds are its single date, fetched once
    assert ("2020-03-01", "2020-03-01", 0) in obs_calls


def test_fetch_observation_vintages_empty_when_series_absent_from_alfred():
    def fake_vdates(series_id, api_key, get=None, page=None):
        return []

    def must_not_call(url):
        raise AssertionError("observations must not be fetched when no vintage dates")

    assert (
        fetch.fetch_observation_vintages(
            "SP500", "K", get=must_not_call, get_vintage_dates=fake_vdates
        )
        == []
    )


def test_run_skips_vintages_for_benchmark_theme():
    """A benchmark-theme series (SP500) has no ALFRED history, so run must not
    vintage-fetch it even under --vintages; its observations still land."""

    def fake_series(series_id, api_key, get=None):
        return {"id": series_id, "title": f"title-{series_id}", "frequency": "Daily"}

    def fake_obs(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    vintage_calls = []

    def fake_vintages(series_id, api_key, start=None, get=None):
        vintage_calls.append(series_id)
        return [{"date": "2026-01-01", "realtime_start": "2026-02-01", "value": 1.0}]

    import tempfile
    import unittest.mock as mock

    with (
        tempfile.TemporaryDirectory() as tmp_path,
        mock.patch.object(
            run_mod.catalog,
            "CATALOG",
            [Series("SP500", "benchmark"), Series("RATE", "rates")],
        ),
    ):
        run_mod.run(
            f"{tmp_path}/fred.db",
            api_key="K",
            now_iso="2026-07-02T00:00:00+00:00",
            fetch_series=fake_series,
            fetch_obs=fake_obs,
            vintages=True,
            fetch_vintages=fake_vintages,
        )
        assert vintage_calls == ["RATE"]  # benchmark skipped, rates fetched


def test_run_with_vintages_fetches_and_writes():
    """Test run-level: run(..., vintages=True, fetch_vintages=<fake>)
    writes vintage rows."""

    def fake_series(series_id, api_key, get=None):
        return {"id": series_id, "title": f"title-{series_id}", "frequency": "Monthly"}

    def fake_obs(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    def fake_vintages(series_id, api_key, start=None, get=None):
        return [
            {"date": "2026-01-01", "realtime_start": "2026-02-01", "value": 1.0},
            {"date": "2026-01-01", "realtime_start": "2026-03-01", "value": 1.1},
        ]

    import tempfile

    with tempfile.TemporaryDirectory() as tmp_path:
        import unittest.mock as mock

        with mock.patch.object(run_mod.catalog, "CATALOG", [Series("A", "rates")]):
            dbp = f"{tmp_path}/fred.db"
            sid, sc, oc = run_mod.run(
                dbp,
                api_key="K",
                now_iso="2026-07-02T00:00:00+00:00",
                fetch_series=fake_series,
                fetch_obs=fake_obs,
                vintages=True,
                fetch_vintages=fake_vintages,
            )
            assert sc == 1
            assert oc == 1
            conn = db.connect(dbp)
            vintage_count = conn.execute("SELECT COUNT(*) FROM observation_vintages").fetchone()[0]
            assert vintage_count == 2


def test_run_vintage_fetch_failure_skips_series_and_continues(capsys):
    """Test run-level: failing vintage fetch skips that series
    printing only the exception class name."""

    def fake_series(series_id, api_key, get=None):
        return {"id": series_id, "title": f"title-{series_id}", "frequency": "Monthly"}

    def fake_obs(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    def flaky_vintages(series_id, api_key, start=None, get=None):
        if series_id == "BAD":
            raise RuntimeError("vintage boom")
        return [{"date": "2026-01-01", "realtime_start": "2026-02-01", "value": 1.0}]

    import tempfile
    import unittest.mock as mock

    with (
        tempfile.TemporaryDirectory() as tmp_path,
        mock.patch.object(
            run_mod.catalog, "CATALOG", [Series("GOOD", "rates"), Series("BAD", "rates")]
        ),
    ):
        dbp = f"{tmp_path}/fred.db"
        sid, sc, oc = run_mod.run(
            dbp,
            api_key="K",
            now_iso="2026-07-02T00:00:00+00:00",
            fetch_series=fake_series,
            fetch_obs=fake_obs,
            vintages=True,
            fetch_vintages=flaky_vintages,
        )
        # Both series counted in success (only vintage fetch failed)
        assert sc == 2
        # Check that RuntimeError was printed without the message
        captured = capsys.readouterr()
        assert "BAD" in captured.err
        assert "RuntimeError" in captured.err
        assert "vintage boom" not in captured.err


def test_run_vintage_write_failure_rolls_back_partial_rows(capsys):
    """Test run-level: a vintage write that fails PARTWAY through (after
    inserting a row directly on the shared, uncommitted connection) must not
    leave that row behind. The nested except must conn.rollback() before the
    next series' upsert_series commits and silently persists it."""

    def fake_series(series_id, api_key, get=None):
        return {"id": series_id, "title": f"title-{series_id}", "frequency": "Monthly"}

    def fake_obs(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    def fake_vintages(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "realtime_start": "2026-02-01", "value": 1.0}]

    def flaky_write_vintages(conn, series_id, rows):
        # Insert one row directly on the open (uncommitted) connection, then
        # blow up before write_observation_vintages' own commit runs -- this
        # simulates executemany failing partway through.
        conn.execute(
            "INSERT INTO observation_vintages "
            "(series_id, date, realtime_start, value) VALUES (?, ?, ?, ?)",
            (series_id, "2026-01-01", "2026-02-01", 1.0),
        )
        raise RuntimeError("vintage write boom")

    import tempfile
    import unittest.mock as mock

    with (
        tempfile.TemporaryDirectory() as tmp_path,
        mock.patch.object(
            run_mod.catalog, "CATALOG", [Series("FIRST", "rates"), Series("SECOND", "rates")]
        ),
        mock.patch.object(run_mod.db, "write_observation_vintages", flaky_write_vintages),
    ):
        dbp = f"{tmp_path}/fred.db"
        sid, sc, oc = run_mod.run(
            dbp,
            api_key="K",
            now_iso="2026-07-02T00:00:00+00:00",
            fetch_series=fake_series,
            fetch_obs=fake_obs,
            vintages=True,
            fetch_vintages=fake_vintages,
        )
        # Both series still counted as successful (only the vintage
        # sub-step failed, and it is skip-and-continue).
        assert sc == 2
        conn = db.connect(dbp)
        # The rollback must have discarded the directly-inserted row
        # for FIRST -- it must not survive to be committed by SECOND's
        # upsert_series.
        count = conn.execute(
            "SELECT COUNT(*) FROM observation_vintages WHERE series_id='FIRST'"
        ).fetchone()[0]
        assert count == 0
        # The series' own observations/metadata (committed by their
        # own writers before the vintage code ran) must survive.
        assert (
            conn.execute("SELECT COUNT(*) FROM observations WHERE series_id='FIRST'").fetchone()[0]
            == 1
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM series WHERE series_id='FIRST'").fetchone()[0] == 1
        )
        captured = capsys.readouterr()
        assert "RuntimeError" in captured.err
        assert "vintage write boom" not in captured.err
