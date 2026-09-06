"""Positive-path tests for the equity-curve exporter: the stock book's index
math (buys are flows, not returns), empty-book gaps, exclusions, thin-book empty."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

from sources.combiners.scorer import db as scorer_db  # noqa: E402

NOW = "2026-08-07T04:13:00+00:00"


def _seed(tmp_path, fills=(), prices=()):
    """fills: (symbol, fill_date, qty, price[, exit_date, exit_price]);
    prices: (symbol, date, close)."""
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    for f in fills:
        symbol, fill_date, qty, price = f[:4]
        exit_date, exit_price = (f[4], f[5]) if len(f) > 4 else (None, None)
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, fill_date, fill_price, quantity,"
            " exit_fill_date, exit_fill_price, order_ref, recorded_at)"
            " VALUES (?, 'acted', 'buy', ?, ?, ?, ?, ?, ?, ?)",
            (symbol, fill_date, price, qty, exit_date, exit_price, f"{symbol}-{fill_date}", NOW),
        )
    conn.executemany("INSERT INTO prices (symbol, price_date, close) VALUES (?, ?, ?)", prices)
    conn.commit()
    conn.close()


# AAA bought 07-31, BBB added 08-04; SPY 630 → 636.3 → 640. Book legs:
# 08-04 (24+55)/(22+50) = +9.72%, 08-05 (25+56)/79 = +2.53% → 81/72 chained.
BOOK = dict(
    fills=[("AAA", "2026-07-31", 2.0, 10.0), ("BBB", "2026-08-04", 1.0, 50.0)],
    prices=[
        ("AAA", "2026-07-31", 11.0),
        ("AAA", "2026-08-04", 12.0),
        ("AAA", "2026-08-05", 12.5),
        ("BBB", "2026-08-04", 55.0),
        ("BBB", "2026-08-05", 56.0),
        ("SPY", "2026-07-31", 630.0),
        ("SPY", "2026-08-04", 636.3),
        ("SPY", "2026-08-05", 640.0),
    ],
)


def _section(tmp_path):
    return data.export_data(str(tmp_path), NOW)["sections"]["equity-curve"]


def test_indexes_rebase_on_the_book_and_buys_are_not_returns(tmp_path):
    _seed(tmp_path, **BOOK)
    sec = _section(tmp_path)
    assert "error" not in sec
    curve = sec["curve"]
    assert curve[0] == {"date": "2026-07-31", "portfolio": 100.0, "spy": 100.0, "cash": None}
    # buy day: the $50 lot joins at its fill price — index +9.72%, never +259%
    assert abs(curve[1]["portfolio"] - 100.0 * 79.0 / 72.0) < 0.01
    assert abs(curve[2]["portfolio"] - 112.5) < 0.01
    assert abs(curve[2]["spy"] - 100.0 * 640.0 / 630.0) < 0.01
    s = sec["curve_summary"]
    assert abs(s["twr"] - 0.125) < 1e-9
    assert abs(s["spy"] - (640.0 / 630.0 - 1.0)) < 1e-9
    assert abs(s["excess"] - (s["twr"] - s["spy"])) < 1e-9
    assert s["positions"] == 2
    assert s["trading_days"] == 3
    assert "excluded" not in s


def test_headline_is_plain_english_tiles_and_a_verdict(tmp_path):
    _seed(tmp_path, **BOOK)
    sec = _section(tmp_path)
    # No cash tile without fred.db — a dash tile would read as "cash earned nothing".
    assert [(t["label"], t["value"]) for t in sec["tiles"]] == [
        ("Your picks", "+12.50%"),
        ("SPY", "+1.59%"),
    ]
    assert sec["verdict"] == {"text": "Ahead of SPY by 10.9 points since Jul 31", "tone": "on"}


def test_cash_tile_and_behind_verdict(tmp_path):
    # Book flat while SPY rises: behind, orange.
    _seed(
        tmp_path,
        fills=[("AAA", "2026-07-31", 1.0, 10.0)],
        prices=[
            ("AAA", "2026-07-31", 10.0),
            ("AAA", "2026-08-04", 10.0),
            ("SPY", "2026-07-31", 630.0),
            ("SPY", "2026-08-04", 640.0),
        ],
    )
    _seed_fred(tmp_path, [("2026-07-31", 3.6)])
    sec = _section(tmp_path)
    assert [t["label"] for t in sec["tiles"]] == ["Your picks", "SPY", "Cash"]
    assert sec["tiles"][0]["value"] == "0.00%"
    assert sec["tiles"][2]["value"] == "+0.04%"  # (1.0001)^4 - 1
    assert sec["verdict"] == {"text": "Behind SPY by 1.6 points since Jul 31", "tone": "off"}


def test_empty_book_days_are_not_charted_and_spy_skips_them_too(tmp_path):
    # Sold out 08-04, empty 08-05/08-06, back in 08-07: SPY's +11% on 08-05
    # happened while nothing was held, so the chart drops those days and the
    # SPY index does not move across the gap.
    _seed(
        tmp_path,
        fills=[
            ("AAA", "2026-07-31", 2.0, 10.0, "2026-08-04", 11.0),
            ("BBB", "2026-08-07", 1.0, 100.0),
        ],
        prices=[
            ("AAA", "2026-07-31", 11.0),
            ("AAA", "2026-08-04", 11.0),
            ("BBB", "2026-08-07", 100.0),
            ("BBB", "2026-08-10", 100.0),
            ("SPY", "2026-07-31", 630.0),
            ("SPY", "2026-08-04", 630.0),
            ("SPY", "2026-08-05", 700.0),
            ("SPY", "2026-08-06", 700.0),
            ("SPY", "2026-08-07", 700.0),
            ("SPY", "2026-08-10", 700.0),
        ],
    )
    sec = _section(tmp_path)
    dates = [r["date"] for r in sec["curve"]]
    assert dates == ["2026-07-31", "2026-08-04", "2026-08-07", "2026-08-10"]
    assert [r["spy"] for r in sec["curve"]] == [100.0, 100.0, 100.0, 100.0]
    assert [r["portfolio"] for r in sec["curve"]] == [100.0, 100.0, 100.0, 100.0]
    assert sec["curve_summary"]["excess"] == 0.0


def test_unpriceable_symbol_leaves_the_line_untouched(tmp_path):
    # NOPX has no close anywhere: valuing it at $0 would print a −36% leg.
    # The scorecard text names it; the chart just doesn't carry it.
    _seed(
        tmp_path, fills=BOOK["fills"] + [("NOPX", "2026-08-04", 1.0, 40.0)], prices=BOOK["prices"]
    )
    sec = _section(tmp_path)
    assert abs(sec["curve_summary"]["twr"] - 0.125) < 1e-9
    assert sec["curve_summary"]["positions"] == 2


def test_thin_book_is_empty_not_error(tmp_path):
    _seed(
        tmp_path,
        fills=[("AAA", "2026-08-04", 1.0, 10.0)],
        prices=[("AAA", "2026-08-04", 10.0), ("SPY", "2026-08-04", 640.0)],
    )
    sec = _section(tmp_path)
    assert "empty" in sec and "error" not in sec


def test_missing_db_degrades(tmp_path):
    sec = _section(tmp_path)  # nothing seeded, no scorer.db at all
    assert "error" in sec


# --- Cash (DFF) benchmark line ------------------------------------------------


def _seed_fred(tmp_path, dff):
    from sources.screeners.fred_screener import db as fred_db

    conn = fred_db.connect(str(tmp_path / "fred.db"))
    fred_db.ensure_schema(conn)
    fred_db.write_observations(conn, "DFF", [{"date": d, "value": v} for d, v in dff])
    conn.commit()
    conn.close()


def test_cash_line_indexes_from_dff(tmp_path):
    _seed(tmp_path, **BOOK)
    # 3.6%/360 = exactly 1bp/day; last observation carries forward to 08-05.
    _seed_fred(tmp_path, [(f"2026-07-{d}", 3.6) for d in (28, 29, 30, 31)])
    sec = _section(tmp_path)
    curve = sec["curve"]
    assert curve[0]["cash"] == 100.0
    assert abs(curve[1]["cash"] - 100.0 * 1.0001**4) < 0.005  # 100.04
    assert abs(curve[2]["cash"] - 100.0 * 1.0001**5) < 0.005  # 100.05
    assert abs(sec["curve_summary"]["cash"] - (1.0001**5 - 1.0)) < 1e-9


def test_cash_is_null_without_fred_db(tmp_path):
    _seed(tmp_path, **BOOK)
    sec = _section(tmp_path)
    assert "curve" in sec  # a missing fred.db never blanks the section
    assert all(r["cash"] is None for r in sec["curve"])
    assert sec["curve_summary"]["cash"] is None
