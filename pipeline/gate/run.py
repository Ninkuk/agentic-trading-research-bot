"""Gate orchestration: the decision loop (Stage 3). Loads the latest
candidates snapshot, masks each candidate, asks an LLM risk-reviewer agent
for a bounded opinion (approve / cut size / veto), resolves it through the
reduce-only guardrail table in `resolve.py`, applies a book-level heat cut,
and writes the immutable decision ledger via `db.py`.

Window-policy (which windows run when, pre-close vs mid-day cadence) is a
Stage 5 scheduler concern, not this module's — `window` here is just an
opaque label persisted on the run header. Replay (`--replay-run`) and the
CLI `main()` are added in Task 7; this module only exposes the library
entry points `load_gate_input` and `run`.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.gate import catalog, db, llm, mask, resolve


def load_gate_input(conn) -> tuple:
    """Read candidates.db `v_gate_input` (all columns) + the latest
    candidates snapshot id. Returns (rows, snapshot_id)."""
    cur = conn.execute("SELECT * FROM v_gate_input")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    snap = conn.execute(
        "SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
    ).fetchone()
    snapshot_id = snap[0] if snap is not None else None
    return rows, snapshot_id


def _resolve_api_key(api_key, dry_run):
    if dry_run:
        return api_key
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "no API key: pass api_key or set ANTHROPIC_API_KEY "
            "(unless dry_run)")
    return key


def _get_proposal(alias, system, user, model, api_key, complete):
    """Live path: call the agent, parse its reply, re-ask once on a
    malformed grammar violation. Returns (proposal, agent_error, body).
    Any error (transport failure or a second malformed reply) is logged
    once, alias-only — never the instrument, never str(e)."""
    error = None
    for attempt in (1, 2):
        try:
            body = complete(system, user, model=model, api_key=api_key)
        except Exception as e:
            error = type(e).__name__
            break
        try:
            return llm.parse_agent(llm.response_text(body)), None, body
        except llm.MalformedResponse:
            error = "MalformedResponse"
            continue
    print(f"warning: gate agent failed for {alias}: {error}", file=sys.stderr)
    return None, error, None


def run(db_path, candidates_db, tau=catalog.TAU, model=catalog.DEFAULT_MODEL,
        api_key=None, complete=llm.complete, window="adhoc", dry_run=False,
        connect_ro=pipeline_common.connect_ro, now_iso=None, id_gen=None,
        only=None) -> tuple:
    """Run one gate pass. Returns (run_id, decision_count, approved_count)."""
    api_key = _resolve_api_key(api_key, dry_run)
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    id_gen = id_gen or (lambda: str(uuid.uuid4()))

    cand_conn = connect_ro(candidates_db)
    try:
        rows, snapshot_id = load_gate_input(cand_conn)
    finally:
        cand_conn.close()

    if only is not None:
        keep = set(only)
        rows = [r for r in rows if r["instrument"] in keep]

    equity = rows[0]["equity"] if rows else 0.0
    config_hash = (rows[0].get("config_hash") if rows else "") or ""
    gcv = catalog.guardrail_config_version(tau, catalog.HEAT_CAP, model,
                                          config_hash)

    aliases = mask.build_mask([r["instrument"] for r in rows])

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        run_id = db.write_run(conn, now_iso, snapshot_id,
                              "dry_run" if dry_run else window, equity,
                              catalog.HEAT_CAP, tau, gcv)

        decisions = []
        model_version = None
        for row in rows:
            instrument = row["instrument"]
            alias = aliases[instrument]
            parsed = mask.parse_input_row(row)
            view = mask.masked_view(parsed, alias, now_iso)
            user = mask.render_user_prompt(view)
            system = catalog.SYSTEM_PROMPT
            p_hash = mask.prompt_hash(system, user)
            checkpoint = catalog.canonical_json({
                "input": parsed, "masked": view, "alias": alias,
                "system": system, "user": user})
            input_hash = mask.sha256_canonical(parsed)

            if dry_run:
                outcome = {"final_shares": row["size_hi"],
                          "decision_maker": "deterministic",
                          "policy_decision": "DryRun", "clamp_fired": 0,
                          "event": None}
                proposal = None
                agent_error = None
            else:
                proposal, agent_error, body = _get_proposal(
                    alias, system, user, model, api_key, complete)
                if body is not None and model_version is None:
                    model_version = llm.response_model(body)
                outcome = resolve.resolve(row["size_lo"], row["size_hi"],
                                         proposal, tau)

            det_shares = row["shares"]
            final_shares = outcome["final_shares"]
            decision = {
                "decision_id": id_gen(),
                "run_id": run_id,
                "decided_at": now_iso,
                "instrument": instrument,
                "direction": row["direction"],
                "input_snapshot_hash": input_hash,
                "checkpoint": checkpoint,
                "det_shares": det_shares,
                "det_stop": row.get("stop_price"),
                "det_score": row.get("det_score"),
                "stop_distance": row.get("stop_distance"),
                "size_lo": row["size_lo"],
                "size_hi": row["size_hi"],
                "agent_action": proposal["action"] if proposal else None,
                "agent_size_mult": proposal["size_mult"] if proposal else None,
                "agent_confidence": proposal["confidence"] if proposal else None,
                "agent_rationale": proposal["rationale"] if proposal else None,
                "agent_error": agent_error,
                "tau": tau,
                "final_shares": final_shares,
                "delta": final_shares - det_shares,
                "clamp_fired": outcome["clamp_fired"],
                "policy_decision": outcome["policy_decision"],
                "decision_maker": outcome["decision_maker"],
                "model_version": None,   # pinned below, once, for the run
                "prompt_hash": p_hash,
                "guardrail_config_version": gcv,
                "_event": outcome["event"],
            }
            decisions.append(decision)

        for d in decisions:
            d["model_version"] = None if dry_run else model_version

        if not dry_run:
            book = [{"instrument": d["instrument"],
                     "det_score": d["det_score"],
                     "final_shares": d["final_shares"],
                     "stop_distance": d["stop_distance"]}
                    for d in decisions if d["policy_decision"] == "Permit"
                    and d["final_shares"] > 0]
            cuts = set(resolve.heat_cut(book, equity, catalog.HEAT_CAP))
            if cuts:
                by_instrument = {d["instrument"]: d for d in decisions}
                for instrument in cuts:
                    d = by_instrument[instrument]
                    d["final_shares"] = 0
                    d["delta"] = 0 - d["det_shares"]
                    d["policy_decision"] = "Deny"
                    d["decision_maker"] = "deterministic"
                    d["_event"] = "heat_cut"

        approved_count = sum(1 for d in decisions
                            if d["policy_decision"] == "Permit"
                            and d["final_shares"] > 0)

        for d in decisions:
            event = d.pop("_event")
            db.write_decision(conn, d)
            events = [("created", now_iso, None)]
            if not dry_run:
                events.append((event, now_iso, None))
            db.write_events(conn, d["decision_id"], events)

        db.finalize_run(conn, run_id, len(decisions),
                        None if dry_run else model_version)
    finally:
        conn.close()

    return run_id, len(decisions), approved_count
