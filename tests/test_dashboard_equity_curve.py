"""Positive-path tests for the equity-curve exporter: index math (deposit
excluded), weekend spy nulls, orphan refusal, and thin-ledger empty."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

from sources.combiners.scorer import db as scorer_db  # noqa: E402

NOW = "2026-08-07T04:13:00+00:00"


def _seed(tmp_path, ledger, transfers=(), spy=()):
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO equity_ledger (obs_date, equity, cash, captured_at)"
        " VALUES (?, ?, 0, '2026-08-06T04:00:00+00:00')",
        ledger,
    )
    conn.executemany(
        "INSERT INTO transfers (obs_date, amount, recorded_at)"
        " VALUES (?, ?, '2026-08-06T04:00:00+00:00')",
        transfers,
    )
    conn.executemany("INSERT INTO prices (symbol, price_date, close) VALUES ('SPY', ?, ?)", spy)
    conn.commit()
    conn.close()


def _section(tmp_path):
    return data.export_data(str(tmp_path), NOW)["sections"]["equity-curve"]


def test_indexes_rebase_and_exclude_deposit(tmp_path):
    _seed(
        tmp_path,
        ledger=[("2026-07-31", 197.0), ("2026-08-04", 303.0), ("2026-08-05", 306.0)],
        transfers=[("2026-08-04", 100.0)],
        spy=[("2026-07-31", 630.0), ("2026-08-04", 636.3), ("2026-08-05", 640.0)],
    )
    sec = _section(tmp_path)
    assert "error" not in sec
    curve = sec["curve"]
    assert curve[0] == {
        "date": "2026-07-31",
        "portfolio": 100.0,
        "spy": 100.0,
        "cash": None,  # no fred.db seeded here
        "flow": 0.0,
    }
    # deposit day: portfolio index +3.05%, never +53.8%
    assert abs(curve[1]["portfolio"] - 103.05) < 0.01
    assert curve[1]["flow"] == 100.0
    assert abs(curve[2]["portfolio"] - 103.05 * (306.0 / 303.0)) < 0.02
    assert abs(curve[2]["spy"] - 100.0 * 640.0 / 630.0) < 0.01
    s = sec["curve_summary"]
    assert abs(s["twr"] - (103.05 * 306.0 / 303.0 / 100.0 - 1.0)) < 1e-3
    assert abs(s["spy"] - (640.0 / 630.0 - 1.0)) < 1e-9
    assert abs(s["excess"] - (s["twr"] - s["spy"])) < 1e-9
    assert s["ledger_dates"] == 3


def test_weekend_rows_compound_portfolio_but_null_spy(tmp_path):
    # 07-26 is a Sunday with no SPY close, so the chart window trims to
    # 07-31..08-04 — but coverage counts uncharted SPY days over the WHOLE
    # ledger (the scorecard's binding): 07-28 in the trimmed-off leading gap
    # and 08-03 interior. Binding the trimmed endpoints would see only 08-03.
    _seed(
        tmp_path,
        ledger=[
            ("2026-07-26", 199.0),
            ("2026-07-31", 200.0),
            ("2026-08-01", 201.0),
            ("2026-08-04", 202.0),
        ],
        spy=[
            ("2026-07-28", 626.0),
            ("2026-07-31", 630.0),
            ("2026-08-03", 638.0),
            ("2026-08-04", 640.0),
        ],
    )
    sec = _section(tmp_path)
    dates = [r["date"] for r in sec["curve"]]
    assert dates == ["2026-07-31", "2026-08-01", "2026-08-04"]
    assert sec["curve"][1]["spy"] is None
    assert abs(sec["curve"][2]["portfolio"] - 101.0) < 0.01  # 202/200 across both legs
    assert sec["curve_summary"]["missing_trading_days"] == 2


def test_orphan_transfer_refuses_with_dates(tmp_path):
    _seed(
        tmp_path,
        ledger=[("2026-07-31", 200.0), ("2026-08-04", 202.0)],
        transfers=[("2026-08-02", 50.0)],
        spy=[("2026-07-31", 630.0), ("2026-08-04", 640.0)],
    )
    sec = _section(tmp_path)
    assert "cannot chart" in sec["error"] and "2026-08-02" in sec["error"]
    assert "curve" not in sec


def test_thin_ledger_is_empty_not_error(tmp_path):
    _seed(tmp_path, ledger=[("2026-08-04", 200.0)], spy=[("2026-08-04", 640.0)])
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
    _seed(
        tmp_path,
        ledger=[("2026-07-31", 197.0), ("2026-08-04", 303.0), ("2026-08-05", 306.0)],
        transfers=[("2026-08-04", 100.0)],
        spy=[("2026-07-31", 630.0), ("2026-08-04", 636.3), ("2026-08-05", 640.0)],
    )
    # 3.6%/360 = exactly 1bp/day; last observation carries forward to 08-05.
    _seed_fred(tmp_path, [(f"2026-07-{d}", 3.6) for d in (28, 29, 30, 31)])
    sec = _section(tmp_path)
    curve = sec["curve"]
    assert curve[0]["cash"] == 100.0
    assert abs(curve[1]["cash"] - 100.0 * 1.0001**4) < 0.005  # 100.04
    assert abs(curve[2]["cash"] - 100.0 * 1.0001**5) < 0.005  # 100.05
    assert abs(sec["curve_summary"]["cash"] - (1.0001**5 - 1.0)) < 1e-9


def test_cash_is_null_without_fred_db(tmp_path):
    _seed(
        tmp_path,
        ledger=[("2026-07-31", 200.0), ("2026-08-04", 202.0)],
        spy=[("2026-07-31", 630.0), ("2026-08-04", 640.0)],
    )
    sec = _section(tmp_path)
    assert "curve" in sec  # a missing fred.db never blanks the section
    assert all(r["cash"] is None for r in sec["curve"])
    assert sec["curve_summary"]["cash"] is None


def test_trader_scorecard_text_includes_cash(tmp_path):
    _seed(
        tmp_path,
        ledger=[("2026-07-31", 200.0), ("2026-08-05", 202.0)],
        spy=[("2026-07-31", 630.0), ("2026-08-05", 640.0)],
    )
    _seed_fred(tmp_path, [("2026-07-31", 3.6)])
    lines = data.export_data(str(tmp_path), NOW)["sections"]["trader-scorecard"]["text_lines"]
    inception = next(ln for ln in lines if ln.strip().startswith("inception"))
    assert inception.split("|")[4].strip() == "0.05%"  # (1.0001)^5 - 1
