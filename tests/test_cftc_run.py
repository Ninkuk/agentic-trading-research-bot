# tests/test_cftc_run.py
from sources.screeners.cftc_screener import db
from sources.screeners.cftc_screener import run as run_mod
from sources.screeners.cftc_screener.catalog import Family, Market

NOW = "2026-07-03T00:00:00+00:00"


def _rows(code, series):
    """series: list of (date, noncomm_long). Newest last (fetch orders ascending)."""
    return [
        {
            "code": code,
            "report_date": d,
            "name": f"name-{code}",
            "noncomm_long": lo,
            "noncomm_short": 0,
            "open_interest": 1000,
        }
        for (d, lo) in series
    ]


def _patch_legacy_catalog(monkeypatch, markets):
    """run() resolves the legacy catalog via catalog.FAMILIES["legacy"].catalog,
    a reference captured at catalog-module import time — patching catalog.CATALOG
    alone does not reach it. Repoint FAMILIES["legacy"] at the same test catalog
    so these market-list monkeypatches actually take effect."""
    monkeypatch.setattr(run_mod.catalog, "CATALOG", markets)
    monkeypatch.setitem(
        run_mod.catalog.FAMILIES,
        "legacy",
        Family("legacy", "6dca-aqww", markets, "cot", run_mod.fetch.LEGACY_FIELDS),
    )


def test_run_happy_path_counts(tmp_path, monkeypatch):
    _patch_legacy_catalog(
        monkeypatch, [Market("A", "Alpha", "metals"), Market("B", "Beta", "energy")]
    )

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
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
    _patch_legacy_catalog(
        monkeypatch, [Market("GOOD", "G", "metals"), Market("BAD", "B", "metals")]
    )

    def flaky(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        if code == "BAD":
            raise RuntimeError("boom")
        return _rows(code, [("2026-06-23", 5)])

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=flaky)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["GOOD"]
    assert "BAD" in capsys.readouterr().err


def test_run_passes_lookback_floor_as_start(tmp_path, monkeypatch):
    _patch_legacy_catalog(monkeypatch, [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        seen.setdefault("start", []).append(start)
        return _rows(code, [("2026-06-16", 1), ("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)  # empty db -> full (start=None)
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)  # incremental -> max - 10 weeks
    # 2026-06-23 minus 10 weeks (70 days) = 2026-04-14
    assert seen["start"] == [None, "2026-04-14"]


def test_run_full_ignores_stored_max(tmp_path, monkeypatch):
    _patch_legacy_catalog(monkeypatch, [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        seen.setdefault("start", []).append(start)
        return _rows(code, [("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)  # populate
    run_mod.run(
        dbp, start="2020-01-01", full=True, now_iso=NOW, fetch_rows=fake_fetch
    )  # full -> CLI start, not lookback
    assert seen["start"] == [None, "2020-01-01"]


def test_run_skips_failing_write_and_continues(tmp_path, monkeypatch, capsys):
    _patch_legacy_catalog(
        monkeypatch, [Market("GOOD", "G", "metals"), Market("BADW", "B", "metals")]
    )

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 5)])

    orig_write = run_mod.db.write_family

    def flaky_write(conn, family, code, rows):
        if code == "BADW":
            raise RuntimeError("disk full")
        return orig_write(conn, family, code, rows)

    monkeypatch.setattr(run_mod.db, "write_family", flaky_write)
    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)
    assert mc == 1  # only GOOD counted a success
    assert "BADW" in capsys.readouterr().err
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT DISTINCT code FROM cot")] == [
        "GOOD"
    ]  # BADW's facts rolled back
    assert (
        conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    )  # snapshot still written


def test_run_all_fail_writes_zero_snapshot(tmp_path, monkeypatch, capsys):
    _patch_legacy_catalog(monkeypatch, [Market("BAD", "B", "metals")])

    def boom(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        raise RuntimeError("nope")

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=boom)
    assert (mc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert conn.execute("SELECT market_count, row_count FROM snapshots").fetchone() == (0, 0)


def test_run_only_selects_subset(tmp_path, monkeypatch):
    _patch_legacy_catalog(
        monkeypatch, [Market("A", "Alpha", "metals"), Market("B", "Beta", "metals")]
    )

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 1)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, only=["B"], now_iso=NOW, fetch_rows=fake_fetch)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["B"]


# --- family extension ---


def _disagg_family(codes):
    return Family(
        "disaggregated",
        "72hh-3qpy",
        [Market(c, f"name-{c}", "metals") for c in codes],
        "cot_disagg",
        [
            ("open_interest", "open_interest_all", int),
            ("mm_long", "m_money_positions_long_all", int),
            ("mm_short", "m_money_positions_short_all", int),
        ],
    )


def test_run_family_routes_dataset_and_writes_family_table(tmp_path, monkeypatch):
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "disaggregated", _disagg_family(["A"]))
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        seen["dataset_id"] = dataset_id
        return [
            {
                "code": code,
                "report_date": "2026-06-23",
                "name": "name-A",
                "open_interest": 100,
                "mm_long": 20,
                "mm_short": 5,
            }
        ]

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    assert seen["dataset_id"] == "72hh-3qpy"
    conn = db.connect(dbp)
    assert conn.execute("SELECT mm_long FROM cot_disagg WHERE code='A'").fetchone()[0] == 20
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 0  # legacy untouched


def test_run_default_family_is_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    # Re-point the LEGACY family's catalog at the patched CATALOG for this test.
    monkeypatch.setitem(
        run_mod.catalog.FAMILIES,
        "legacy",
        Family(
            "legacy",
            "6dca-aqww",
            [Market("A", "Alpha", "metals")],
            "cot",
            run_mod.fetch.LEGACY_FIELDS,
        ),
    )

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 7)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)  # no family kwarg
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM cot_disagg").fetchone()[0] == 0


def test_run_family_lookback_floor_uses_family_table(tmp_path, monkeypatch):
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "disaggregated", _disagg_family(["A"]))
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        seen.setdefault("start", []).append(start)
        return [
            {
                "code": code,
                "report_date": "2026-06-23",
                "mm_long": 1,
                "mm_short": 0,
                "open_interest": 10,
            }
        ]

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    # 2026-06-23 minus 10 weeks (70 days) = 2026-04-14, read from cot_disagg
    assert seen["start"] == [None, "2026-04-14"]


def test_run_never_logs_exception_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    monkeypatch.setitem(
        run_mod.catalog.FAMILIES,
        "legacy",
        Family(
            "legacy",
            "6dca-aqww",
            [Market("A", "Alpha", "metals")],
            "cot",
            run_mod.fetch.LEGACY_FIELDS,
        ),
    )

    def boom(code, dataset_id=None, field_map=None, app_token=None, since=None, start=None):
        raise RuntimeError("SECRET-TOKEN-abc123")  # message must NOT leak

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=boom)
    err = capsys.readouterr().err
    assert "A" in err  # code is logged
    assert "SECRET-TOKEN-abc123" not in err  # message is not
    assert "RuntimeError" in err  # class is
