import json

import pytest

from pipeline.trials import db as tdb
from pipeline.trials import run as trun
from sources.common import monitor_common
from sources.screeners.stock_analysis_screener import db as stocks_db_mod
from pipeline.leads import db as leads_db

NOW = "2026-07-04T12:00:00+00:00"
COLS = {"price": "REAL", "low": "REAL", "averageVolume": "REAL"}


def _make_stocks(path, snapshots):
    conn = stocks_db_mod.connect(path)
    stocks_db_mod.ensure_schema(conn, COLS)
    for cap, quotes in snapshots:
        data = {sym: {"price": p, "low": lo, "averageVolume": 1e6}
                for sym, (p, lo) in quotes.items()}
        stocks_db_mod.write_snapshot(conn, cap, "test", data, list(COLS))
    conn.close()


def _make_calendar(path):
    conn = monitor_common.connect(path)
    monitor_common.ensure_schema(conn)
    conn.close()


def _make_leads(path, rows):
    conn = leads_db.connect(path)
    leads_db.ensure_schema(conn)
    sid = leads_db.write_snapshot(conn, NOW)
    leads_db.write_leads(conn, sid, [
        {"instrument": i, "instrument_kind": "stock", "direction": d,
         "signal": "quality_composite", "signal_type": "quality",
         "implementation": "cross_sectional", "horizon_band": "weeks",
         "score": 1.0, "rank_pct": None, "as_of_date": a, "details": "{}"}
        for i, d, a in rows])
    conn.close()


def _world(tmp_path):
    paths = {"trials": str(tmp_path / "trials.db"),
             "leads": str(tmp_path / "leads.db"),
             "stocks": str(tmp_path / "stocks.db"),
             "etfs": str(tmp_path / "missing-etfs.db"),
             "calendar": str(tmp_path / "market_calendar.db")}
    _make_stocks(paths["stocks"], [
        ("2026-07-01T20:00:00+00:00", {"WIN": (100.0, 99.0)}),
        ("2026-07-02T20:00:00+00:00", {"WIN": (110.0, 109.0)}),
        ("2026-07-03T20:00:00+00:00", {"WIN": (121.0, 120.0)}),
    ])
    _make_calendar(paths["calendar"])
    _make_leads(paths["leads"], [("WIN", "long", "2026-07-01")])
    return paths


def test_register_and_dedupe(tmp_path):
    dbp = str(tmp_path / "trials.db")
    tid, created = trun.run_register(dbp, "promote", "ADV 5M",
                                     '{"floor": 5000000}',
                                     family="liq", now_iso=NOW, git_rev="abc")
    tid2, created2 = trun.run_register(dbp, "promote", "again",
                                       '{"floor": 5000000}',
                                       family="liq", now_iso=NOW)
    assert created and not created2 and tid == tid2


def test_register_rejects_bad_json(tmp_path):
    with pytest.raises(ValueError):
        trun.run_register(str(tmp_path / "t.db"), "promote", "d", "{not json",
                          now_iso=NOW)


def test_evaluate_writes_result_and_notices_null_dsr(tmp_path, capsys):
    paths = _world(tmp_path)
    tid, _ = trun.run_register(paths["trials"], "leads", "funnel v1", "{}",
                               family="funnel", now_iso=NOW)
    result = trun.run_evaluate(paths["trials"], tid,
                               leads_db=paths["leads"],
                               stocks_db=paths["stocks"],
                               etfs_db=paths["etfs"],
                               calendar_db=paths["calendar"], now_iso=NOW)
    assert result["n_obs"] == 1
    assert result["avg_return"] == pytest.approx(0.10)  # 110 -> 121
    assert result["dsr_at_eval"] is None                # N=1, sd unavailable
    assert result["n_at_eval"] == 1
    err = capsys.readouterr().err
    assert "etfs" in err and "OperationalError" in err  # missing etfs skipped
    conn = tdb.connect(paths["trials"])
    stored = conn.execute("SELECT n_obs, sharpe FROM trial_results "
                          "WHERE trial_id=?", (tid,)).fetchone()
    assert stored[0] == 1 and stored[1] is None         # single obs: no SR
    detail = json.loads(conn.execute(
        "SELECT detail FROM trial_results WHERE trial_id=?",
        (tid,)).fetchone()[0])
    assert detail["entry_lag"] == 1 and "max_gap_days" in detail
    conn.close()


def test_evaluate_unknown_trial_returns_none(tmp_path, capsys):
    paths = _world(tmp_path)
    assert trun.run_evaluate(paths["trials"], 42, leads_db=paths["leads"],
                             stocks_db=paths["stocks"], etfs_db=paths["etfs"],
                             calendar_db=paths["calendar"], now_iso=NOW) is None
    assert "42" in capsys.readouterr().err


def test_evaluate_requires_calendar(tmp_path, capsys):
    paths = _world(tmp_path)
    tid, _ = trun.run_register(paths["trials"], "leads", "d", "{}", now_iso=NOW)
    result = trun.run_evaluate(paths["trials"], tid, leads_db=paths["leads"],
                               stocks_db=paths["stocks"],
                               etfs_db=paths["etfs"],
                               calendar_db=str(tmp_path / "no-cal.db"),
                               now_iso=NOW)
    assert result is None
    assert "OperationalError" in capsys.readouterr().err


def test_leaderboard_appends_live_dsr(tmp_path):
    dbp = str(tmp_path / "trials.db")
    conn = tdb.connect(dbp)
    tdb.ensure_schema(conn)
    for i, sr in enumerate((0.5, 0.3, 0.8)):
        tid, _ = tdb.register_trial(conn, "promote", f"t{i}", {"x": i}, NOW,
                                    family="liq")
        tdb.write_result(conn, tid, {
            "evaluated_at": NOW, "window_start": "2026-06-01",
            "window_end": "2026-07-01", "n_obs": 24, "sharpe": sr,
            "skew": -0.3, "kurtosis": 4.0, "hit_rate": 0.6,
            "avg_return": 0.01, "max_drawdown": 0.05, "dsr_at_eval": None,
            "n_at_eval": 3, "detail": "{}"})
    conn.close()
    rows = trun.run_leaderboard(dbp, family="liq")
    assert len(rows) == 1
    assert rows[0]["n_trials"] == 3
    assert rows[0]["best_sharpe"] == pytest.approx(0.8)
    assert rows[0]["dsr_live"] == pytest.approx(0.9838475849035124, rel=1e-6)


def test_main_cli_register_smoke(tmp_path, capsys):
    dbp = str(tmp_path / "trials.db")
    trun.main(["--db", dbp, "--register", "--stage", "promote",
               "--description", "ADV 5M", "--params", '{"floor": 5000000}',
               "--family", "liq"])
    out = capsys.readouterr().out
    assert "trial" in out
