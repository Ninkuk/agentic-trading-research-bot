"""The two Track-record cards that replaced the text scorecard: "Your trades"
(the deliberate journal, research-backed or freelance) and "Trading the
signals" (alignment and fill cost per horizon). Both read the scorecard
module's own query helpers, so the card and the terminal report agree."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import data  # noqa: E402

from sources.combiners.scorer import db as scorer_db  # noqa: E402

NOW = "2026-08-07T04:13:00+00:00"


def _connect(tmp_path):
    conn = scorer_db.connect(str(tmp_path / "scorer.db"))
    scorer_db.ensure_schema(conn)
    return conn


def _fill(conn, symbol, fill_date, price, exit_date=None, exit_price=None, **extra):
    cols = [
        "symbol",
        "action",
        "side",
        "fill_date",
        "fill_price",
        "quantity",
        "exit_fill_date",
        "exit_fill_price",
        "recorded_at",
        *extra,
    ]
    vals = [
        symbol,
        "acted",
        "buy",
        fill_date,
        price,
        1.0,
        exit_date,
        exit_price,
        NOW,
        *extra.values(),
    ]
    conn.execute(
        f"INSERT INTO decisions ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        vals,
    )


def _verdict(conn, symbol, verdict_date, verdict="buy"):
    conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, doc, recorded_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (symbol, verdict, verdict_date, f"{symbol}-{verdict_date}.md", NOW),
    )


def _flagged(conn, symbol, score_sum, fill_price, side="buy", horizons=(5, 10)):
    """A composite flag the human traded: the snapshot, its matured outcome
    rows (entry close 100), and the acted decision matched to it."""
    conn.execute(
        "INSERT OR IGNORE INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-01', '2026-07-02', ?, 9, 1, 0)",
        (NOW,),
    )
    for h in horizons:
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at) VALUES (1, '2026-07-01', ?, ?, 4, 2, 2, ?, '2026-07-02', 100.0,"
            " 500.0, '2026-07-09', 104.0, 0.04, 0.01, ?)",
            (symbol, score_sum, h, NOW),
        )
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, composite_snapshot_id, composite_date,"
        " opinion_score_sum, opinion_total, fill_date, fill_price, quantity, recorded_at)"
        " VALUES (?, 'acted', ?, 1, '2026-07-01', ?, 4, '2026-07-03', ?, 1.0, ?)",
        (symbol, side, score_sum, fill_price, NOW),
    )


def _sections(tmp_path):
    return data.export_data(str(tmp_path), NOW)["sections"]


# --- Your trades -------------------------------------------------------------


def test_your_trades_merges_research_backed_and_freelance_newest_first(tmp_path):
    conn = _connect(tmp_path)
    _verdict(conn, "AAA", "2026-07-01")
    _fill(conn, "AAA", "2026-07-02", 10.0)
    _fill(conn, "BBB", "2026-07-05", 20.0, "2026-07-20", 22.0)
    _fill(conn, "DRIP", "2026-07-06", 5.0, placed_agent="drip")  # automatic: never listed
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["your-trades"]
    assert "error" not in sec
    rows = sec["rows"]
    assert [r["symbol"] for r in rows] == ["BBB", "AAA"]
    bbb, aaa = rows
    assert aaa["backed_by"] == "Research" and aaa["verdict_date"] == "2026-07-01"
    assert aaa["status"] == "open" and aaa["realized_return"] is None
    assert bbb["backed_by"] == "Freelance" and bbb["verdict_date"] is None
    assert bbb["status"] == "closed" and abs(bbb["realized_return"] - 0.10) < 1e-9
    assert {c["key"] for c in sec["columns"]} >= {
        "symbol",
        "side",
        "fill_date",
        "backed_by",
        "verdict_date",
        "status",
        "realized_return",
        "decision_id",
    }


def test_your_trades_tiles_count_the_journal_and_the_research_share(tmp_path):
    conn = _connect(tmp_path)
    _verdict(conn, "AAA", "2026-07-01")
    _fill(conn, "AAA", "2026-07-02", 10.0)
    _fill(conn, "BBB", "2026-07-05", 20.0, "2026-07-20", 22.0)
    _fill(conn, "CCC", "2026-07-06", 30.0)
    conn.commit()
    conn.close()
    tiles = {t["label"]: t for t in _sections(tmp_path)["your-trades"]["tiles"]}
    assert tiles["Trades journaled"]["value"] == 3
    assert tiles["Trades journaled"]["band"] == "2 open · 1 closed"
    assert tiles["Backed by research"]["value"] == "1 of 3"


def test_your_trades_refuses_to_grade_under_five_closed(tmp_path):
    conn = _connect(tmp_path)
    _fill(conn, "AAA", "2026-07-02", 10.0, "2026-07-20", 11.0)
    _fill(conn, "BBB", "2026-07-05", 20.0)
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["your-trades"]
    assert sec["verdict"] == {"text": "1 closed trade, too few to grade", "tone": "mid"}


def test_your_trades_grades_the_average_closed_return_at_five(tmp_path):
    conn = _connect(tmp_path)
    for i, ret in enumerate((0.10, 0.10, 0.10, -0.05, -0.05)):
        _fill(conn, f"S{i}", "2026-07-02", 100.0, "2026-07-20", 100.0 * (1 + ret))
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["your-trades"]
    assert sec["verdict"] == {"text": "Closed trades averaged +4.0%", "tone": "on"}


def test_your_trades_empty_when_nothing_deliberate_is_journaled(tmp_path):
    conn = _connect(tmp_path)
    _fill(conn, "DRIP", "2026-07-06", 5.0, placed_agent="recurring")
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["your-trades"]
    assert sec["rows"] == [] and sec["empty"]
    assert sec["verdict"] is None


# --- Trading the signals -----------------------------------------------------


def test_trading_the_signals_rows_per_horizon_with_counts_and_costs(tmp_path):
    conn = _connect(tmp_path)
    _flagged(conn, "BULL", 3, fill_price=99.0)  # sided with a bull flag, paid 1% less
    _flagged(conn, "BEAR", -3, fill_price=101.0)  # bought into a bear flag: contrarian
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["trading-the-signals"]
    assert "error" not in sec
    assert [r["horizon"] for r in sec["rows"]] == [5, 10]
    row = sec["rows"][0]
    assert row["n"] == 2 and row["agreed"] == 1 and row["contrarian"] == 1
    assert row["no_opinion"] == 0
    # n=2 < N_MIN: the averages stay suppressed, exactly as the text report does
    assert row["avg_entry_slippage"] is None and row["avg_fill_lag_days"] is None


def test_trading_the_signals_tiles_speak_plainly(tmp_path):
    conn = _connect(tmp_path)
    for i in range(5):
        _flagged(conn, f"B{i}", 3, fill_price=99.0)
    _flagged(conn, "X", -3, fill_price=99.0)
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["trading-the-signals"]
    tiles = {t["label"]: t for t in sec["tiles"]}
    assert tiles["Sided with the signal"]["value"] == "5 of 6"
    assert tiles["Sided with the signal"]["band"] == "1 went against it · 0 had no signal"
    assert tiles["Paid vs the plan"]["value"] == "1.00% less"
    assert tiles["Paid vs the plan"]["tone"] == "on"
    assert tiles["Days to fill"]["value"] == "1.0"
    row = sec["rows"][0]
    assert abs(row["avg_entry_slippage"] + 0.01) < 1e-9 and row["avg_fill_lag_days"] == 1.0


def test_trading_the_signals_cost_tile_waits_for_five_trades(tmp_path):
    conn = _connect(tmp_path)
    _flagged(conn, "BULL", 3, fill_price=102.0)
    conn.commit()
    conn.close()
    tiles = {t["label"]: t for t in _sections(tmp_path)["trading-the-signals"]["tiles"]}
    assert tiles["Paid vs the plan"]["value"] == "too few trades"
    assert tiles["Paid vs the plan"]["band"] == "1 graded, 5 needed"
    assert tiles["Paid vs the plan"]["tone"] is None


def test_trading_the_signals_empty_before_any_flagged_trade_matures(tmp_path):
    conn = _connect(tmp_path)
    _fill(conn, "AAA", "2026-07-02", 10.0)  # freelance: no flag behind it
    conn.commit()
    conn.close()
    sec = _sections(tmp_path)["trading-the-signals"]
    assert sec["rows"] == [] and sec["empty"] and sec["tiles"] == []
