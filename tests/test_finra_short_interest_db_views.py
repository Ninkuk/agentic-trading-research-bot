# tests/test_finra_short_interest_db_views.py
import pytest

from sources.screeners.finra_short_interest import db

_COLS = [
    "symbol",
    "settlement_date",
    "current_short_qty",
    "previous_short_qty",
    "avg_daily_volume",
    "days_to_cover",
    "change_pct",
    "revision_flag",
    "market_class",
]


def _row(symbol, sdate, cur, adv=200000, dtc=1.0, prev=None):
    return {
        "symbol": symbol,
        "settlement_date": sdate,
        "current_short_qty": cur,
        "previous_short_qty": prev,
        "avg_daily_volume": adv,
        "days_to_cover": dtc,
        "change_pct": 0.0,
        "revision_flag": None,
        "market_class": "NNM",
    }


def _insert(conn, rows):
    """Insert directly (bypassing replace_settlement's delete-by-date) so
    multiple symbols can share a settlement date."""
    db.upsert_securities(conn, [dict(r, issue_name="X") for r in rows])
    conn.executemany(
        f"INSERT INTO short_interest ({','.join(_COLS)}) "
        f"VALUES ({','.join(':' + c for c in _COLS)})",
        rows,
    )
    conn.commit()


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_latest_only_max_settlement_and_liquid():
    conn = _fresh()
    _insert(
        conn, [_row("A", "2024-06-14", 100, adv=200000), _row("A", "2024-06-28", 120, adv=200000)]
    )
    _insert(conn, [_row("B", "2024-06-28", 999, adv=50000)])  # illiquid -> out
    rows = conn.execute(
        "SELECT symbol, settlement_date, current_short_qty FROM v_latest"
    ).fetchall()
    assert len(rows) == 1
    assert tuple(rows[0]) == ("A", "2024-06-28", 120)


def test_v_high_days_to_cover_threshold_and_liquidity():
    conn = _fresh()
    _insert(conn, [_row("A", "2024-06-28", 100, adv=200000, dtc=6.0)])  # in
    _insert(conn, [_row("B", "2024-06-28", 100, adv=200000, dtc=4.0)])  # dtc<5 out
    _insert(conn, [_row("C", "2024-06-28", 100, adv=50000, dtc=9.0)])  # illiquid out
    syms = {r[0] for r in conn.execute("SELECT symbol FROM v_high_days_to_cover")}
    assert syms == {"A"}


def test_v_short_interest_spikes_prior_and_trailing_average():
    conn = _fresh()
    # four trailing settlements at 100000, latest jumps to 300000, prev=150000
    _insert(
        conn,
        [
            _row("A", "2024-04-15", 100000, adv=200000),
            _row("A", "2024-04-30", 100000, adv=200000),
            _row("A", "2024-05-15", 100000, adv=200000),
            _row("A", "2024-05-31", 100000, adv=200000),
            _row("A", "2024-06-14", 300000, adv=200000, prev=150000),
        ],
    )
    cur, prev, si_change, base, base_ratio = conn.execute(
        "SELECT current_short_qty, previous_short_qty, si_change, base, "
        "base_ratio FROM v_short_interest_spikes WHERE symbol='A'"
    ).fetchone()
    assert (cur, prev) == (300000, 150000)
    assert si_change == pytest.approx(2.0)  # 300000 / 150000 (file's prior)
    assert base == pytest.approx(100000.0)  # trailing settlement average
    assert base_ratio == pytest.approx(3.0)  # 300000 / 100000


def test_v_symbol_history_returns_full_series():
    conn = _fresh()
    _insert(conn, [_row("A", "2024-06-14", 100), _row("A", "2024-06-28", 120)])
    dates = [
        r[0]
        for r in conn.execute(
            "SELECT settlement_date FROM v_symbol_history WHERE symbol='A' ORDER BY settlement_date"
        )
    ]
    assert dates == ["2024-06-14", "2024-06-28"]
