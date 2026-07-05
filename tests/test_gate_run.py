import json

import pytest

from pipeline.gate import db as gdb
from pipeline.gate import llm
from pipeline.gate import run as grun
from pipeline.promote import db as pdb

NOW = "2026-07-04T20:00:00+00:00"


def _mk_candidates(path, rows, equity=100000.0):
    conn = pdb.connect(path)
    pdb.ensure_schema(conn)
    sid = pdb.write_snapshot(conn, NOW, equity=equity, regime_scalar=1.0,
                             leads_snapshot_id=1, config_hash="c" * 64)
    pdb.write_candidates(conn, sid, rows)
    pdb.finalize_snapshot(conn, sid)
    conn.close()
    return sid


def _cand(instrument, det_score=0.96, shares=100, stop_distance=8.0,
          price=200.0, **over):
    row = {"instrument": instrument, "instrument_kind": "etf",
           "direction": "long", "det_score": det_score,
           "horizon_band": "weeks",
           "signals": json.dumps([{"signal": "cot_commercial_extreme",
                                   "det_score": det_score,
                                   "as_of_date": "2026-06-30"}]),
           "price": price, "atr": 4.0, "sector": "metals",
           "next_earnings_date": None, "shares": shares,
           "stop_price": price - stop_distance,
           "stop_distance": stop_distance, "risk_dollars": 1000.0,
           "realized_risk": shares * stop_distance, "size_lo": 0,
           "size_hi": shares, "as_of_date": "2026-06-30",
           "details": json.dumps([{"asset_class": "metals",
                                   "commercial_index": 96.0,
                                   "code": "088691"}])}
    row.update(over)
    return row


def _completer(script):
    """script: alias-independent queue of reply texts (or Exceptions)."""
    calls = {"prompts": [], "n": 0}

    def fake_complete(system, user, *, model, api_key, post=None, sleep=None):
        calls["prompts"].append((system, user))
        item = script[min(calls["n"], len(script) - 1)]
        calls["n"] += 1
        if isinstance(item, Exception):
            raise item
        return {"model": "claude-sonnet-5-20260203",
                "content": [{"type": "text", "text": item}]}
    return fake_complete, calls


def _reply(action="approve", size_mult=1.0, confidence=0.9):
    return json.dumps({"action": action, "size_mult": size_mult,
                       "confidence": confidence, "rationale": "r"})


def test_run_mixed_outcomes_and_reduce_only_invariant(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD"), _cand("SLV", det_score=0.97),
                           _cand("SPY", det_score=0.98)])
    complete, calls = _completer([
        _reply(size_mult=0.5),                       # GLD: cut to 50
        _reply(action="veto", confidence=0.9),       # SLV: honored veto
        _reply(action="veto", confidence=0.3),       # SPY: DISCARDED veto
    ])
    gpath = str(tmp_path / "gate.db")
    run_id, n, approved = grun.run(gpath, cpath, api_key="K",
                                   complete=complete, window="pre_close",
                                   now_iso=NOW,
                                   id_gen=iter(f"id-{i}" for i in range(9)).__next__)
    assert n == 3
    conn = gdb.connect(gpath)
    rows = {r["instrument"]: r for r in gdb.decisions_for_run(conn, run_id)}
    assert rows["GLD"]["final_shares"] == 50
    assert rows["GLD"]["decision_maker"] == "agent"
    assert rows["SLV"]["final_shares"] == 0
    assert rows["SPY"]["final_shares"] == 100          # cliff: full size
    assert rows["SPY"]["decision_maker"] == "deterministic"
    # reduce-only, provable:
    assert conn.execute("SELECT COUNT(*) FROM gate_decisions "
                        "WHERE decision_maker='agent' AND delta > 0"
                        ).fetchone()[0] == 0
    # discarded veto surfaces as an alert; honored veto does not
    alerts = {r[0] for r in conn.execute(
        "SELECT instrument FROM v_gate_alerts")}
    assert alerts == {"SPY"}
    book = {r[0] for r in conn.execute(
        "SELECT instrument FROM v_approved_book")}
    assert book == {"GLD", "SPY"}
    header = gdb.run_row(conn, run_id)
    assert header["model_version"] == "claude-sonnet-5-20260203"
    assert header["window"] == "pre_close"
    conn.close()


def test_run_prompt_leak_regression(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    complete, calls = _completer([_reply()])
    grun.run(str(tmp_path / "gate.db"), cpath, api_key="K",
             complete=complete, now_iso=NOW)
    system, user = calls["prompts"][0]
    for leaked in ("GLD", "088691", "200.0", "192.0", "2026-06-30"):
        assert leaked not in system + user, leaked


def test_run_malformed_twice_falls_through_deterministic(tmp_path, capsys):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    complete, calls = _completer(["not json", "still not json"])
    gpath = str(tmp_path / "gate.db")
    run_id, _, _ = grun.run(gpath, cpath, api_key="K", complete=complete,
                            now_iso=NOW)
    conn = gdb.connect(gpath)
    row = gdb.decisions_for_run(conn, run_id)[0]
    assert row["agent_error"] == "MalformedResponse"
    assert row["decision_maker"] == "deterministic"
    assert row["final_shares"] == 100
    assert calls["n"] == 2                       # exactly one re-ask
    err = capsys.readouterr().err
    assert "CAND_A" in err and "GLD" not in err  # alias-only hygiene
    conn.close()


def test_run_unexpected_response_shape_falls_through_deterministic(tmp_path):
    # A well-formed HTTP 200 with an unexpected shape (empty content list)
    # must be treated as a malformed reply — one re-ask, then the
    # deterministic fallback — not let a raw KeyError/IndexError escape and
    # halt the run (see llm.response_text hardening).
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    calls = {"n": 0}
    bad_body = {"model": "m", "content": []}

    def fake_complete(system, user, *, model, api_key, post=None, sleep=None):
        calls["n"] += 1
        return bad_body

    gpath = str(tmp_path / "gate.db")
    run_id, n, approved = grun.run(gpath, cpath, api_key="K",
                                   complete=fake_complete, now_iso=NOW)
    assert calls["n"] == 2                       # exactly one re-ask
    conn = gdb.connect(gpath)
    row = gdb.decisions_for_run(conn, run_id)[0]
    assert row["agent_error"] == "MalformedResponse"
    assert row["decision_maker"] == "deterministic"
    assert row["final_shares"] == row["size_hi"] == 100
    header = gdb.run_row(conn, run_id)
    assert header["decision_count"] == n == 1     # header finalized
    conn.close()


def test_run_api_error_falls_through(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    complete, _ = _completer([RuntimeError("secret url")])
    gpath = str(tmp_path / "gate.db")
    run_id, _, _ = grun.run(gpath, cpath, api_key="K", complete=complete,
                            now_iso=NOW)
    conn = gdb.connect(gpath)
    row = gdb.decisions_for_run(conn, run_id)[0]
    assert row["agent_error"] == "RuntimeError"
    assert row["final_shares"] == 100
    conn.close()


def test_run_heat_cut_zeroes_lowest_scores_first(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    # three approvals, each realized risk 100*40=4000; budget 6% of 100k=6000
    _mk_candidates(cpath, [
        _cand("AAA", det_score=0.99, stop_distance=40.0),
        _cand("BBB", det_score=0.95, stop_distance=40.0),
        _cand("CCC", det_score=0.97, stop_distance=40.0)])
    complete, _ = _completer([_reply()])
    gpath = str(tmp_path / "gate.db")
    run_id, _, approved = grun.run(gpath, cpath, api_key="K",
                                   complete=complete, now_iso=NOW)
    conn = gdb.connect(gpath)
    rows = {r["instrument"]: r for r in gdb.decisions_for_run(conn, run_id)}
    # ascending (det_score, instrument): BBB then CCC zeroed; AAA survives
    assert rows["BBB"]["policy_decision"] == "Deny"
    assert rows["CCC"]["policy_decision"] == "Deny"
    assert rows["AAA"]["policy_decision"] == "Permit"
    assert approved == 1
    events = [r[0] for r in conn.execute(
        "SELECT event FROM gate_decision_events WHERE decision_id=? "
        "ORDER BY seq", (rows["BBB"]["decision_id"],))]
    assert events == ["created", "heat_cut"]
    conn.close()


def test_run_dry_run_no_api_calls_and_excluded_from_book(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    complete, calls = _completer([_reply()])
    gpath = str(tmp_path / "gate.db")
    run_id, n, _ = grun.run(gpath, cpath, complete=complete, dry_run=True,
                            now_iso=NOW)                 # no api_key needed
    assert calls["n"] == 0
    conn = gdb.connect(gpath)
    row = gdb.decisions_for_run(conn, run_id)[0]
    assert row["policy_decision"] == "DryRun"
    assert row["prompt_hash"] is not None                # prompts still rendered
    assert conn.execute("SELECT COUNT(*) FROM v_approved_book"
                        ).fetchone()[0] == 0
    assert gdb.run_row(conn, run_id)["window"] == "dry_run"
    conn.close()


def test_run_api_backend_requires_api_key_unless_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    with pytest.raises(ValueError):
        grun.run(str(tmp_path / "g.db"), cpath, now_iso=NOW, backend="api")
    import os.path
    assert not os.path.exists(str(tmp_path / "g.db"))


def test_run_default_backend_needs_no_api_key(tmp_path, monkeypatch):
    # the claude-cli backend is subscription-authenticated — the strictly-
    # no-ANTHROPIC_API_KEY policy path must not demand a key
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD")])
    complete, calls = _completer([_reply()])
    run_id, n, approved = grun.run(str(tmp_path / "gate.db"), cpath,
                                   complete=complete, now_iso=NOW)
    assert n == 1 and approved == 1 and calls["n"] == 1


def test_run_default_complete_is_backend_aware():
    assert grun._complete_for("claude-cli", None) is llm.complete_cli
    assert grun._complete_for("api", None) is llm.complete
    marker = object()
    assert grun._complete_for("api", marker) is marker


def test_run_only_filter(tmp_path):
    cpath = str(tmp_path / "candidates.db")
    _mk_candidates(cpath, [_cand("GLD"), _cand("SLV")])
    complete, calls = _completer([_reply()])
    gpath = str(tmp_path / "gate.db")
    run_id, n, _ = grun.run(gpath, cpath, api_key="K", complete=complete,
                            now_iso=NOW, only=["GLD"])
    assert n == 1
