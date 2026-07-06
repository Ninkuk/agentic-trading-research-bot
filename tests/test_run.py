import os

import pytest

from sources.screeners.stock_analysis_screener.catalog import DataPoint
from sources.screeners.stock_analysis_screener.db import connect
from sources.screeners.stock_analysis_screener.run import run, select_ids


def test_select_ids_applies_only_and_exclude():
    assert select_ids(["a", "b", "c"], ["a", "b"], ["b"]) == ["a"]
    assert select_ids(["a", "b", "c"], None, ["b"]) == ["a", "c"]


def test_select_ids_dedupes_and_drops_blank_tokens():
    # `--only "pe, pe,,roe"` splits to ['pe', ' pe', '', 'roe']; without
    # sanitizing, dup/empty ids reach the metrics INSERT and crash it.
    assert select_ids(["a", "b"], ["pe", " pe ", "", "roe", "roe"], None) == ["pe", "roe"]


def test_select_ids_strips_exclude_tokens():
    assert select_ids(["a", "b", "c"], None, [" b "]) == ["a", "c"]


def test_run_fetches_catalog_for_the_requested_screener_type(tmp_path):
    # --type e must pull the ETF catalog, not the stocks one — the two
    # screeners have different data-point id sets.
    db_path = str(tmp_path / "e.db")
    seen = {}

    def fake_catalog(type_):
        seen["catalog_type"] = type_
        return ([DataPoint("price", "Stock Price", "Price & Volume", False)], 1)

    def fake_data(ids, type_):
        assert type_ == "e"
        return {"SPY": {"price": 744.78}}

    run(
        db_path,
        type_="e",
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-04T00:00:00+00:00",
    )
    assert seen["catalog_type"] == "e"


def test_run_writes_snapshot_end_to_end(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = (
        [
            DataPoint("price", "Stock Price", "Price & Volume", False),
            DataPoint("sector", "Sector", "Company Info", False),
        ],
        2,
    )
    data = {"AAA": {"price": 10.0, "sector": "Tech"}, "BBB": {"price": 20.0, "sector": "Energy"}}

    def fake_catalog(type_):
        return catalog

    def fake_data(ids, type_):
        assert ids == ["price", "sector"]
        assert type_ == "s"
        return data

    sid, n = run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-02T00:00:00+00:00",
    )
    assert n == 2
    conn = connect(db_path)
    stored = conn.execute("SELECT price, sector FROM metrics WHERE symbol='AAA'").fetchone()
    assert stored == (10.0, "Tech")
    # catalog persisted
    assert conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0] == 2


def test_run_twice_appends_snapshot_and_v_latest_returns_newest(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = ([DataPoint("price", "Stock Price", "Price & Volume", False)], 1)

    def fake_catalog(type_):
        return catalog

    def make_fetch(data):
        def fake_data(ids, type_):
            return data

        return fake_data

    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=make_fetch({"AAA": {"price": 10.0}}),
        now_iso="2026-07-01T00:00:00+00:00",
    )
    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=make_fetch({"AAA": {"price": 20.0}}),
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
    prices = [r[0] for r in conn.execute("SELECT price FROM v_latest").fetchall()]
    assert prices == [20.0]


def test_run_keep_days_prunes_old_snapshot_through_run(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = ([DataPoint("price", "Stock Price", "Price & Volume", False)], 1)

    def fake_catalog(type_):
        return catalog

    def make_fetch(data):
        def fake_data(ids, type_):
            return data

        return fake_data

    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=make_fetch({"AAA": {"price": 10.0}}),
        now_iso="2026-06-01T00:00:00+00:00",
    )
    run(
        db_path,
        keep_days=7,
        fetch_catalog=fake_catalog,
        fetch_data=make_fetch({"AAA": {"price": 20.0}}),
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    prices = [r[0] for r in conn.execute("SELECT price FROM metrics").fetchall()]
    assert prices == [20.0]


def test_run_exclude_omits_column_from_metrics_table(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = (
        [
            DataPoint("price", "Stock Price", "Price & Volume", False),
            DataPoint("sector", "Sector", "Company Info", False),
        ],
        2,
    )

    def fake_catalog(type_):
        return catalog

    def fake_data(ids, type_):
        assert ids == ["price"]
        return {"AAA": {"price": 10.0}}

    run(
        db_path,
        exclude=["sector"],
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}
    assert "price" in cols
    assert "sector" not in cols


def test_run_propagates_fetch_error_and_writes_no_snapshot(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = ([DataPoint("price", "Stock Price", "Price & Volume", False)], 1)

    def fake_catalog(type_):
        return catalog

    def failing_fetch(ids, type_):
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        run(
            db_path,
            fetch_catalog=fake_catalog,
            fetch_data=failing_fetch,
            now_iso="2026-07-02T00:00:00+00:00",
        )

    # ensure_schema/write_snapshot only run after a successful fetch_data call,
    # so the db file is never created and no snapshot rows exist.
    assert not os.path.exists(db_path)


def test_run_drops_reserved_column_id_from_catalog(tmp_path):
    db_path = str(tmp_path / "s.db")
    # "symbol" collides with the base metrics column; without the
    # _RESERVED_COLUMNS filter this leads to a duplicate-column INSERT.
    catalog = (
        [
            DataPoint("symbol", "Symbol", "Company Info", False),
            DataPoint("price", "Stock Price", "Price & Volume", False),
        ],
        2,
    )

    def fake_catalog(type_):
        return catalog

    def fake_data(ids, type_):
        # "symbol" collides with the base metrics column; it must be dropped
        # from ids before reaching fetch_data.
        assert ids == ["price"]
        return {"AAA": {"symbol": "AAA", "price": 10.0}, "BBB": {"symbol": "BBB", "price": 20.0}}

    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    price = conn.execute("SELECT price FROM metrics WHERE symbol='AAA'").fetchone()[0]
    assert price == 10.0


def test_run_skips_data_point_with_no_values(tmp_path):
    # A data-point that is null for every symbol (e.g. a pro-only field on a
    # free plan) should not create a metrics column — this curbs unbounded
    # ALTER-driven column growth over successive runs.
    db_path = str(tmp_path / "s.db")
    catalog = (
        [
            DataPoint("price", "Stock Price", "Price & Volume", False),
            DataPoint("proField", "Pro Metric", "Pro", True),
        ],
        2,
    )

    def fake_catalog(type_):
        return catalog

    def fake_data(ids, type_):
        return {"AAA": {"price": 10.0, "proField": None}, "BBB": {"price": 20.0, "proField": None}}

    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}
    assert "price" in cols
    assert "proField" not in cols  # all-null column skipped


def test_run_warns_on_short_universe_but_still_writes(tmp_path, capsys):
    db_path = str(tmp_path / "s.db")
    # Catalog claims 5 stocks but fetch_data only returns 2.
    catalog = (
        [
            DataPoint("price", "Stock Price", "Price & Volume", False),
            DataPoint("sector", "Sector", "Company Info", False),
        ],
        5,
    )

    def fake_catalog(type_):
        return catalog

    def fake_data(ids, type_):
        return {
            "AAA": {"price": 10.0, "sector": "Tech"},
            "BBB": {"price": 20.0, "sector": "Energy"},
        }

    run(
        db_path,
        fetch_catalog=fake_catalog,
        fetch_data=fake_data,
        now_iso="2026-07-02T00:00:00+00:00",
    )

    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    symbols = {r[0] for r in conn.execute("SELECT symbol FROM v_latest").fetchall()}
    assert symbols == {"AAA", "BBB"}
