"""Gate orchestration: the decision loop (Stage 3). Loads the latest
candidates snapshot, masks each candidate, asks an LLM risk-reviewer agent
for a bounded opinion (approve / cut size / veto), resolves it through the
reduce-only guardrail table in `resolve.py`, applies a book-level heat cut,
and writes the immutable decision ledger via `db.py`.

Window-policy (which windows run when, pre-close vs mid-day cadence) is a
Stage 5 scheduler concern, not this module's — `window` here is just an
opaque label persisted on the run header.

`replay()` is the deterministic auditor: given a run_id, it re-derives every
decision from the stored checkpoint (never from live inputs) and diffs the
recomputed outcome against what was written. `main()` is the CLI, dispatching
either to a fresh gate `run()` or to `replay()`.
"""
import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.gate import catalog, db, llm, mask, resolve

_DIFF_FIELDS = ("input_snapshot_hash", "prompt_hash", "final_shares", "delta",
                "clamp_fired", "policy_decision", "decision_maker")


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


def _recompute_decision(row: dict, header: dict) -> dict:
    """Re-derive one decision's outcome from its stored checkpoint (never
    from live data) plus the run header's tau. Dry-run rows re-derive as the
    same deterministic size_hi pass-through the original run used — they
    never go through `resolve.resolve`."""
    checkpoint = json.loads(row["checkpoint"])
    input_hash = mask.sha256_canonical(checkpoint["input"])
    p_hash = mask.prompt_hash(checkpoint["system"], checkpoint["user"])
    proposal = (None if row["agent_error"] is not None
                or row["agent_action"] is None else
                {"action": row["agent_action"],
                 "size_mult": row["agent_size_mult"],
                 "confidence": row["agent_confidence"],
                 "rationale": row["agent_rationale"] or ""})
    if header["window"] == "dry_run":
        outcome = {"final_shares": row["size_hi"], "decision_maker": "deterministic",
                   "policy_decision": "DryRun", "clamp_fired": 0}
    else:
        outcome = resolve.resolve(row["size_lo"], row["size_hi"], proposal,
                                  header["tau"])
    return {"decision_id": row["decision_id"], "instrument": row["instrument"],
            "det_shares": row["det_shares"], "det_score": row["det_score"],
            "stop_distance": row["stop_distance"],
            "input_snapshot_hash": input_hash, "prompt_hash": p_hash,
            "final_shares": outcome["final_shares"],
            "delta": outcome["final_shares"] - row["det_shares"],
            "clamp_fired": outcome["clamp_fired"],
            "policy_decision": outcome["policy_decision"],
            "decision_maker": outcome["decision_maker"]}


def replay(db_path, run_id, live=False, complete=llm.complete, api_key=None,
          now_iso=None) -> bool:
    """Deterministic audit of a past run: re-derive every decision from its
    stored checkpoint (the authoritative record) and diff the recomputed
    outcome against what was written. Offline (default) makes ZERO writes.

    `live=True` additionally re-asks the agent with the exact stored prompt,
    prints the counterfactual next to the stored proposal, and appends one
    `replayed` event per decision — the only write live mode performs; the
    return value still reflects the offline (stored-proposal) diff.

    Returns True iff every decision matches on all diffed fields. Unknown
    run_id prints to stderr and returns False."""
    try:
        conn = pipeline_common.connect_ro(db_path)
    except sqlite3.OperationalError as e:
        print(f"replay: {type(e).__name__}", file=sys.stderr)
        return False
    try:
        header = db.run_row(conn, run_id)
        if header is None:
            print(f"replay: unknown run_id {run_id}", file=sys.stderr)
            return False

        rows = db.decisions_for_run(conn, run_id)
        recomputed = {r["decision_id"]: _recompute_decision(r, header)
                     for r in rows}

        if header["window"] != "dry_run":
            book = [r for r in recomputed.values()
                    if r["policy_decision"] == "Permit" and r["final_shares"] > 0]
            cuts = set(resolve.heat_cut(book, header["equity"], header["heat_cap"]))
            for r in recomputed.values():
                if r["instrument"] in cuts:
                    r["final_shares"] = 0
                    r["delta"] = 0 - r["det_shares"]
                    r["policy_decision"] = "Deny"
                    r["decision_maker"] = "deterministic"

        clean = True
        for row in rows:
            rec = recomputed[row["decision_id"]]
            for field in _DIFF_FIELDS:
                if rec[field] != row[field]:
                    clean = False
                    print(f"replay mismatch decision={row['decision_id']} "
                          f"field={field} stored={row[field]!r} "
                          f"recomputed={rec[field]!r}")
    finally:
        conn.close()

    if live:
        now_iso = now_iso or datetime.now(timezone.utc).isoformat()
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "no API key: pass api_key or set ANTHROPIC_API_KEY "
                "for --live replay")
        model = header["model_version"] or catalog.DEFAULT_MODEL
        write_conn = db.connect(db_path)
        try:
            for row in rows:
                checkpoint = json.loads(row["checkpoint"])
                try:
                    body = complete(checkpoint["system"], checkpoint["user"],
                                    model=model, api_key=key)
                    detail = llm.response_text(body)
                except Exception as e:
                    detail = type(e).__name__
                print(f"[live-replay] decision={row['decision_id']} "
                      f"instrument={row['instrument']} "
                      f"stored_action={row['agent_action']} "
                      f"stored_size_mult={row['agent_size_mult']} "
                      f"counterfactual={detail}")
                db.write_events(write_conn, row["decision_id"],
                                [("replayed", now_iso, detail)])
        finally:
            write_conn.close()

    return clean


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="gate", description="Stage 3 gate: LLM risk-review decision loop")
    p.add_argument("--db", required=True)
    p.add_argument("--candidates-db")
    p.add_argument("--tau", type=float, default=catalog.TAU)
    p.add_argument("--model", default=catalog.DEFAULT_MODEL)
    p.add_argument("--window", choices=("pre_close", "pre_open", "adhoc"),
                   default="adhoc")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", default=None,
                   help="comma-separated instruments to keep")
    p.add_argument("--replay", type=int, default=None, metavar="RUN_ID",
                   help="deterministically audit a past run instead of gating")
    p.add_argument("--live", action="store_true",
                   help="with --replay, also ask the agent again and log "
                        "the counterfactual (the only write it performs)")
    a = p.parse_args(argv)

    if a.replay is not None:
        if not replay(a.db, a.replay, live=a.live):
            raise SystemExit(1)
        return

    if not a.candidates_db:
        p.error("--candidates-db is required unless --replay is given")

    only = a.only.split(",") if a.only else None
    run_id, n, approved = run(a.db, a.candidates_db, tau=a.tau, model=a.model,
                              window=a.window, dry_run=a.dry_run, only=only)
    print(f"gate run {run_id}: {n} decisions, {approved} approved "
          f"({'dry_run' if a.dry_run else a.window})")


if __name__ == "__main__":
    main()
