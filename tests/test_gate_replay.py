import json

import pytest

from pipeline.gate import db as gdb
from pipeline.gate import run as grun

# reuse the fixture helpers from the run tests
from tests.test_gate_run import _mk_candidates, _cand, _completer, _reply

NOW = "2026-07-04T20:00:00+00:00"


def _gate_world(tmp_path, replies, cands=None):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, cands or [
        _cand("AAA", det_score=0.99, stop_distance=40.0),
        _cand("BBB", det_score=0.95, stop_distance=40.0),
        _cand("CCC", det_score=0.97, stop_distance=40.0)])
    complete, _ = _completer(replies)
    gpath = str(tmp_path / "gate.db")
    run_id, _, _ = grun.run(gpath, cpath, api_key="K", complete=complete,
                            now_iso=NOW)
    return gpath, run_id


def test_offline_replay_reproduces_heat_cut_book_and_writes_nothing(tmp_path):
    gpath, run_id = _gate_world(tmp_path, [_reply()])
    import hashlib, pathlib
    before = hashlib.sha256(pathlib.Path(gpath).read_bytes()).hexdigest()
    assert grun.replay(gpath, run_id) is True
    after = hashlib.sha256(pathlib.Path(gpath).read_bytes()).hexdigest()
    assert before == after                       # strictly read-only


def test_offline_replay_uses_read_only_connection(tmp_path, monkeypatch):
    gpath, run_id = _gate_world(tmp_path, [_reply()])

    def _forbid_writable_connect(*args, **kwargs):
        raise AssertionError("writable connect in offline replay")

    monkeypatch.setattr(grun.db, "connect", _forbid_writable_connect)
    assert grun.replay(gpath, run_id) is True


def test_replay_detects_tampered_row(tmp_path):
    gpath, run_id = _gate_world(tmp_path, [_reply()])
    # tamper at INSERT time (triggers forbid mutation): forge a copycat run
    conn = gdb.connect(gpath)
    rows = gdb.decisions_for_run(conn, run_id)
    forged = dict(rows[0])
    forged["decision_id"] = "forged-1"
    forged["final_shares"] = forged["final_shares"] + 7   # drifted outcome
    rid2 = gdb.write_run(conn, NOW, 3, "pre_close", 100000.0, 0.06, 0.5,
                         rows[0]["guardrail_config_version"])
    forged["run_id"] = rid2
    gdb.write_decision(conn, forged)
    conn.close()
    assert grun.replay(gpath, rid2) is False


def test_live_replay_appends_replayed_events_only(tmp_path):
    gpath, run_id = _gate_world(tmp_path, [_reply()])
    complete, calls = _completer([_reply(size_mult=0.1)])
    assert grun.replay(gpath, run_id, live=True, complete=complete,
                       api_key="K", now_iso=NOW) is True
    conn = gdb.connect(gpath)
    n_replayed = conn.execute("SELECT COUNT(*) FROM gate_decision_events "
                              "WHERE event='replayed'").fetchone()[0]
    assert n_replayed == conn.execute(
        "SELECT COUNT(*) FROM gate_decisions WHERE run_id=?",
        (run_id,)).fetchone()[0]
    assert calls["n"] == n_replayed              # one counterfactual each
    # original decision rows untouched (still the stored final_shares)
    assert grun.replay(gpath, run_id) is True
    conn.close()


def test_main_replay_exit_codes(tmp_path):
    gpath, run_id = _gate_world(tmp_path, [_reply()])
    grun.main(["--db", gpath, "--replay", str(run_id)])   # exits 0 = returns
    with pytest.raises(SystemExit):
        grun.main(["--db", gpath, "--replay", "9999"])    # unknown run
