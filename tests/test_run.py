from screener.catalog import DataPoint
from screener.db import connect
from screener.run import run, select_ids


def test_select_ids_applies_only_and_exclude():
    assert select_ids(["a", "b", "c"], ["a", "b"], ["b"]) == ["a"]
    assert select_ids(["a", "b", "c"], None, ["b"]) == ["a", "c"]


def test_run_writes_snapshot_end_to_end(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = ([
        DataPoint("price", "Stock Price", "Price & Volume", False),
        DataPoint("sector", "Sector", "Company Info", False),
    ], 2)
    data = {"AAA": {"price": 10.0, "sector": "Tech"},
            "BBB": {"price": 20.0, "sector": "Energy"}}

    def fake_catalog():
        return catalog

    def fake_data(ids, type_):
        assert ids == ["price", "sector"]
        assert type_ == "s"
        return data

    sid, n = run(db_path, fetch_catalog=fake_catalog, fetch_data=fake_data,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 2
    conn = connect(db_path)
    stored = conn.execute(
        "SELECT price, sector FROM metrics WHERE symbol='AAA'").fetchone()
    assert stored == (10.0, "Tech")
    # catalog persisted
    assert conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0] == 2
