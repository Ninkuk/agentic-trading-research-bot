import json

from pipeline.trials import db

NOW = "2026-07-04T12:00:00+00:00"


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _result(**over):
    r = {"evaluated_at": NOW, "window_start": "2026-06-01",
         "window_end": "2026-07-01", "n_obs": 24, "sharpe": 0.5,
         "skew": -0.1, "kurtosis": 3.2, "hit_rate": 0.6, "avg_return": 0.01,
         "max_drawdown": 0.08, "dsr_at_eval": None, "n_at_eval": 1,
         "detail": json.dumps({"max_gap_days": 3, "skipped": 2,
                               "scored": 24, "truncated": 5})}
    r.update(over)
    return r


def test_schema_and_idempotence():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"trials", "trial_results", "snapshots", "v_latest_results",
            "v_trial_history", "v_family_leaderboard",
            "v_evaluation_coverage"} <= names
    db.ensure_schema(conn)


def test_canonical_params_is_order_insensitive():
    j1, h1 = db.canonical_params({"a": 1, "b": [2, 3]})
    j2, h2 = db.canonical_params({"b": [2, 3], "a": 1})
    assert j1 == j2 == '{"a":1,"b":[2,3]}'
    assert h1 == h2 and len(h1) == 64


def test_register_trial_dedupes_within_stage_family():
    conn = _fresh()
    t1, created1 = db.register_trial(conn, "promote", "ADV floor 5M",
                                     {"floor": 5000000}, NOW,
                                     family="stage2-liquidity", git_rev="abc")
    t2, created2 = db.register_trial(conn, "promote", "same knobs again",
                                     {"floor": 5000000}, NOW,
                                     family="stage2-liquidity")
    assert created1 and not created2 and t1 == t2
    # same params in a DIFFERENT family or stage is a DIFFERENT trial
    t3, created3 = db.register_trial(conn, "promote", "other family",
                                     {"floor": 5000000}, NOW, family="other")
    t4, created4 = db.register_trial(conn, "leads", "other stage",
                                     {"floor": 5000000}, NOW,
                                     family="stage2-liquidity")
    assert created3 and created4 and len({t1, t3, t4}) == 3
    assert db.family_size(conn, "stage2-liquidity") == 2


def test_trial_row_roundtrip():
    conn = _fresh()
    tid, _ = db.register_trial(conn, "promote", "d", {"x": 1}, NOW)
    row = db.trial_row(conn, tid)
    assert row["stage"] == "promote" and row["family"] == "default"
    assert json.loads(row["params"]) == {"x": 1}
    assert db.trial_row(conn, 999) is None


def test_results_and_family_latest_sharpes():
    conn = _fresh()
    a, _ = db.register_trial(conn, "promote", "a", {"x": 1}, NOW, family="f")
    b, _ = db.register_trial(conn, "promote", "b", {"x": 2}, NOW, family="f")
    db.write_result(conn, a, _result(evaluated_at="2026-07-01T00:00:00+00:00",
                                     sharpe=0.3))
    db.write_result(conn, a, _result(evaluated_at="2026-07-04T00:00:00+00:00",
                                     sharpe=0.5))          # latest for a
    db.write_result(conn, b, _result(sharpe=None))         # NULL: excluded
    assert sorted(db.family_latest_sharpes(conn, "f")) == [0.5]
    row = conn.execute("SELECT n_trials, best_sharpe FROM v_family_leaderboard "
                       "WHERE family='f'").fetchone()
    assert row == (2, 0.5)


def test_coverage_view_reads_detail_json():
    conn = _fresh()
    tid, _ = db.register_trial(conn, "promote", "d", {"x": 1}, NOW)
    db.write_result(conn, tid, _result())
    row = conn.execute("SELECT n_obs, max_gap_days, skipped, scored, truncated "
                       "FROM v_evaluation_coverage").fetchone()
    assert row == (24, 3, 2, 24, 5)


def test_prune_never_touches_trials_or_results():
    conn = _fresh()
    tid, _ = db.register_trial(conn, "promote", "d", {"x": 1},
                               "2026-01-01T00:00:00+00:00")
    db.write_result(conn, tid, _result(evaluated_at="2026-01-01T00:00:00+00:00"))
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00")
    db.write_snapshot(conn, NOW)
    assert db.prune(conn, keep_days=30, now_iso=NOW) == 1
    assert conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM trial_results").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
