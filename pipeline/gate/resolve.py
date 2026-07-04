"""The outcome-mapping table as pure code: tau rule, code clamp, book-level
heat check. All guardrails live here and in db triggers — never in prompts."""
import math


def resolve(size_lo: int, size_hi: int, proposal, tau: float) -> dict:
    """One candidate's resolution (Permit layer; heat/dry-run overlay runs
    downstream). proposal=None is the error/fallback path.

    Pinned cliff: a low-confidence veto is DISCARDED (deterministic full
    size) — tau exists so noisy caution cannot de-lever the trusted book;
    every discarded veto is logged and surfaced by v_gate_alerts."""
    if proposal is None or proposal["confidence"] < tau:
        return {"final_shares": size_hi, "decision_maker": "deterministic",
                "policy_decision": "Permit", "clamp_fired": 0,
                "event": "approved"}
    if proposal["action"] == "veto":
        return {"final_shares": 0, "decision_maker": "agent",
                "policy_decision": "Permit", "clamp_fired": 0,
                "event": "rejected"}
    mult = proposal["size_mult"]
    raw = math.floor(size_hi * mult)
    final = min(size_hi, max(size_lo, raw))
    return {"final_shares": final, "decision_maker": "agent",
            "policy_decision": "Permit",
            "clamp_fired": 1 if (mult < 0.0 or mult > 1.0) else 0,
            "event": "approved"}


def heat_cut(book: list, equity: float, heat_cap: float) -> list:
    """Instruments to zero so sum(final_shares*stop_distance) fits under
    heat_cap*equity — whole positions, ascending (det_score, instrument),
    v1 has no partial shaves. Uses REALIZED risk (final_shares*stop), not
    Stage 2's theoretical risk_dollars."""
    budget = heat_cap * equity
    live = [dict(p) for p in book if p["final_shares"] > 0]
    total = sum(p["final_shares"] * (p["stop_distance"] or 0.0) for p in live)
    cuts = []
    for p in sorted(live, key=lambda p: (p["det_score"], p["instrument"])):
        if total <= budget:
            break
        total -= p["final_shares"] * (p["stop_distance"] or 0.0)
        cuts.append(p["instrument"])
    return cuts
