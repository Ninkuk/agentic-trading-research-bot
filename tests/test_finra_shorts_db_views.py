# tests/test_finra_shorts_db_views.py
import pytest

from finra_short_volume import db

_COLS = ["symbol", "date", "short_volume", "short_exempt_volume",
         "total_volume", "short_ratio", "market"]


def _rows(symbol, series):
    """series: list of (date, short_ratio, total_volume). short_volume is
    derived so the stored ratio is exact."""
    return [{"symbol": symbol, "date": d,
             "short_volume": int(round(ratio * tv)),
             "short_exempt_volume": 0, "total_volume": tv,
             "short_ratio": ratio, "market": "Q"}
            for d, ratio, tv in series]


def _insert(conn, rows):
    """Insert directly (bypassing replace_day's delete-by-date) so multiple
    symbols can share a date."""
    db.upsert_securities(conn, rows)
    conn.executemany(
        f"INSERT INTO short_volume ({','.join(_COLS)}) "
        f"VALUES ({','.join(':' + c for c in _COLS)})", rows)
    conn.commit()


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_latest_only_max_date_and_liquid():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-13", 0.4, 200000),
                              ("2024-06-14", 0.6, 200000)]))
    _insert(conn, _rows("B", [("2024-06-14", 0.9, 50000)]))   # illiquid -> excluded
    got = {r[0]: r[1] for r in conn.execute(
        "SELECT symbol, short_ratio FROM v_latest")}
    assert set(got) == {"A"}                       # B dropped, only latest date
    assert got["A"] == pytest.approx(0.6)


def test_v_high_short_ratio_threshold():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-14", 0.6, 200000)]))  # >=0.5 -> in
    _insert(conn, _rows("B", [("2024-06-14", 0.4, 200000)]))  # <0.5 -> out
    syms = {r[0] for r in conn.execute("SELECT symbol FROM v_high_short_ratio")}
    assert syms == {"A"}


def test_v_ratio_spikes_against_trailing_average():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-10", 0.2, 200000),
                              ("2024-06-11", 0.2, 200000),
                              ("2024-06-12", 0.2, 200000),
                              ("2024-06-13", 0.2, 200000),
                              ("2024-06-14", 0.6, 200000)]))  # latest jumps
    ratio, base, spike = conn.execute(
        "SELECT short_ratio, base, spike_ratio FROM v_ratio_spikes "
        "WHERE symbol='A'").fetchone()
    assert ratio == pytest.approx(0.6)
    assert base == pytest.approx(0.2)
    assert spike == pytest.approx(3.0)


def test_v_short_streaks_below_threshold_day_splits_run():
    conn = _fresh()
    # 3 elevated, 1 below (present but excluded -> breaks run), 3 elevated again
    _insert(conn, _rows("A", [("2024-06-10", 0.6, 200000),
                              ("2024-06-11", 0.6, 200000),
                              ("2024-06-12", 0.6, 200000),
                              ("2024-06-13", 0.3, 200000),
                              ("2024-06-14", 0.6, 200000),
                              ("2024-06-15", 0.6, 200000),
                              ("2024-06-16", 0.6, 200000)]))
    streaks = sorted((r[0], r[1]) for r in conn.execute(
        "SELECT streak_days, active FROM v_short_streaks WHERE symbol='A'"))
    # two runs of 3; the later one is active (reaches the max stored date)
    assert streaks == [(3, 0), (3, 1)]
