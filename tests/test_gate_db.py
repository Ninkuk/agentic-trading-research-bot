import pytest
import sqlite3

from pipeline.gate import db

NOW = "2026-07-04T20:00:00+00:00"


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _run(conn, **over):
    args = {"captured_at": NOW, "candidates_snapshot_id": 3,
            "window": "pre_close", "equity": 100000.0, "heat_cap": 0.06,
            "tau": 0.5, "guardrail_config_version": "g" * 64}
    args.update(over)
    return db.write_run(conn, **args)


def _decision(run_id, **over):
    row = {"decision_id": "d-1", "run_id": run_id, "decided_at": NOW,
           "instrument": "GLD", "direction": "long",
           "input_snapshot_hash": "i" * 64, "checkpoint": "{}",
           "det_shares": 125, "det_stop": 192.0, "det_score": 0.96,
           "stop_distance": 8.0, "size_lo": 0, "size_hi": 125,
           "agent_action": "approve", "agent_size_mult": 0.8,
           "agent_confidence": 0.7, "agent_rationale": "ok",
           "agent_error": None, "tau": 0.5, "final_shares": 100,
           "delta": -25, "clamp_fired": 0, "policy_decision": "Permit",
           "decision_maker": "agent", "model_version": "claude-sonnet-5-x",
           "prompt_hash": "p" * 64, "guardrail_config_version": "g" * 64}
    row.update(over)
    return row


def test_schema_views_and_no_prune():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"gate_runs", "gate_decisions", "gate_decision_events",
            "v_approved_book", "v_gate_alerts", "v_delta_history",
            "v_decision_makers"} <= names
    db.ensure_schema(conn)                 # idempotent (triggers included)
    assert not hasattr(db, "prune")        # gate.db is NEVER pruned


def test_decisions_are_append_only_by_trigger():
    conn = _fresh()
    rid = _run(conn)
    db.write_decision(conn, _decision(rid))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE gate_decisions SET final_shares=999")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM gate_decisions")
    db.write_events(conn, "d-1", [("created", NOW, None)])
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM gate_decision_events")


def test_run_lifecycle_and_event_sequencing():
    conn = _fresh()
    rid = _run(conn)
    db.write_decision(conn, _decision(rid))
    db.write_events(conn, "d-1", [("created", NOW, None),
                                  ("approved", NOW, None)])
    assert db.max_event_seq(conn, "d-1") == 2
    db.finalize_run(conn, rid, decision_count=1,
                    model_version="claude-sonnet-5-x")
    row = db.run_row(conn, rid)
    assert row["decision_count"] == 1
    assert row["model_version"] == "claude-sonnet-5-x"
    assert db.decisions_for_run(conn, rid)[0]["instrument"] == "GLD"


def test_v_approved_book_excludes_deny_dryrun_zero_and_old_runs():
    conn = _fresh()
    old = _run(conn, captured_at="2026-07-01T00:00:00+00:00")
    db.write_decision(conn, _decision(old, decision_id="old-1",
                                      instrument="OLD"))
    rid = _run(conn)
    db.write_decision(conn, _decision(rid, decision_id="a", instrument="AAA"))
    db.write_decision(conn, _decision(rid, decision_id="b", instrument="BBB",
                                      policy_decision="Deny", final_shares=0,
                                      delta=-125,
                                      decision_maker="deterministic"))
    db.write_decision(conn, _decision(rid, decision_id="c", instrument="CCC",
                                      policy_decision="DryRun",
                                      decision_maker="deterministic"))
    db.write_decision(conn, _decision(rid, decision_id="d", instrument="DDD",
                                      agent_action="veto", final_shares=0,
                                      delta=-125))
    book = [r[0] for r in conn.execute(
        "SELECT instrument FROM v_approved_book")]
    assert book == ["AAA"]


def test_v_gate_alerts_predicates():
    conn = _fresh()
    rid = _run(conn)
    db.write_decision(conn, _decision(rid, decision_id="clamp",
                                      instrument="A", clamp_fired=1))
    db.write_decision(conn, _decision(rid, decision_id="err", instrument="B",
                                      agent_error="HTTPError",
                                      decision_maker="deterministic"))
    db.write_decision(conn, _decision(rid, decision_id="deny", instrument="C",
                                      policy_decision="Deny", final_shares=0,
                                      decision_maker="deterministic"))
    db.write_decision(conn, _decision(rid, decision_id="dveto",
                                      instrument="D", agent_action="veto",
                                      agent_confidence=0.3, final_shares=125,
                                      delta=0,
                                      decision_maker="deterministic"))
    db.write_decision(conn, _decision(rid, decision_id="clean",
                                      instrument="E"))
    alerts = {r[0] for r in conn.execute(
        "SELECT instrument FROM v_gate_alerts")}
    assert alerts == {"A", "B", "C", "D"}          # honored vetoes absent


def test_v_delta_history_and_decision_makers():
    conn = _fresh()
    rid = _run(conn)
    db.write_decision(conn, _decision(rid, decision_id="1", instrument="A",
                                      agent_action="veto", final_shares=0,
                                      delta=-125))
    db.write_decision(conn, _decision(rid, decision_id="2", instrument="B",
                                      decision_maker="deterministic",
                                      agent_action="veto",
                                      agent_confidence=0.2,
                                      final_shares=125, delta=0))
    db.write_decision(conn, _decision(rid, decision_id="3", instrument="C",
                                      clamp_fired=1))
    hist = conn.execute("SELECT n_decisions, n_vetoes, discarded_vetoes, "
                        "clamps FROM v_delta_history WHERE run_id=?",
                        (rid,)).fetchone()
    assert hist == (3, 2, 1, 1)
    makers = dict(conn.execute(
        "SELECT decision_maker, n FROM v_decision_makers WHERE run_id=?",
        (rid,)).fetchall())
    assert makers == {"agent": 2, "deterministic": 1}
