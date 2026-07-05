import pytest

from pipeline.gate import resolve


def _p(action="approve", size_mult=1.0, confidence=0.9):
    return {"action": action, "size_mult": size_mult,
            "confidence": confidence, "rationale": "r"}


def test_outcome_agent_approve_full_and_cut():
    full = resolve.resolve(0, 100, _p(), 0.5)
    assert (full["final_shares"], full["decision_maker"],
            full["policy_decision"], full["clamp_fired"],
            full["event"]) == (100, "agent", "Permit", 0, "approved")
    cut = resolve.resolve(0, 100, _p(size_mult=0.5), 0.5)
    assert cut["final_shares"] == 50 and cut["decision_maker"] == "agent"


def test_outcome_honored_veto():
    v = resolve.resolve(0, 100, _p(action="veto", confidence=0.51), 0.5)
    assert (v["final_shares"], v["decision_maker"], v["event"]) == \
        (0, "agent", "rejected")


def test_outcome_tau_fallthrough_discards_low_confidence_veto():
    # the pinned cliff: veto @ 0.49 -> FULL size, deterministic
    d = resolve.resolve(0, 100, _p(action="veto", confidence=0.49), 0.5)
    assert (d["final_shares"], d["decision_maker"], d["event"]) == \
        (100, "deterministic", "approved")


def test_outcome_agent_error_falls_through():
    d = resolve.resolve(0, 100, None, 0.5)
    assert (d["final_shares"], d["decision_maker"], d["event"]) == \
        (100, "deterministic", "approved")


def test_clamp_fires_on_out_of_range_mult_but_never_exceeds_hi():
    c = resolve.resolve(0, 100, _p(size_mult=1.7), 0.5)
    assert (c["final_shares"], c["clamp_fired"]) == (100, 1)
    n = resolve.resolve(0, 100, _p(size_mult=-0.3), 0.5)
    assert (n["final_shares"], n["clamp_fired"]) == (0, 1)


def test_final_shares_floor_not_round():
    c = resolve.resolve(0, 125, _p(size_mult=0.999), 0.5)
    assert c["final_shares"] == 124


def test_heat_cut_orders_by_score_then_instrument():
    book = [
        {"instrument": "AAA", "det_score": 0.99, "final_shares": 100,
         "stop_distance": 40.0},   # risk 4000
        {"instrument": "BBB", "det_score": 0.95, "final_shares": 100,
         "stop_distance": 30.0},   # risk 3000
        {"instrument": "CCC", "det_score": 0.95, "final_shares": 100,
         "stop_distance": 20.0},   # risk 2000  (ties BBB on score)
    ]
    # equity 100k, cap 6% -> 6000 budget; total 9000. Ascending order:
    # (0.95, BBB) first -> zero BBB (risk drops to 6000, fits). CCC survives.
    cut = resolve.heat_cut(book, equity=100_000.0, heat_cap=0.06)
    assert cut == ["BBB"]


def test_heat_cut_multiple_until_fits_and_noop_when_under():
    book = [{"instrument": i, "det_score": s, "final_shares": 100,
             "stop_distance": 30.0}
            for i, s in (("A", 0.99), ("B", 0.98), ("C", 0.97))]
    cut = resolve.heat_cut(book, equity=100_000.0, heat_cap=0.03)  # 3000 budget
    assert cut == ["C", "B"]   # ascending score: C (0.97) then B (0.98)
    assert resolve.heat_cut(book, equity=1e9, heat_cap=0.06) == []


def test_heat_cut_ignores_zero_share_rows():
    book = [{"instrument": "A", "det_score": 0.9, "final_shares": 0,
             "stop_distance": 999.0},
            {"instrument": "B", "det_score": 0.95, "final_shares": 10,
             "stop_distance": 10.0}]
    assert resolve.heat_cut(book, equity=100_000.0, heat_cap=0.06) == []


def test_resolve_fractional_quantizes_to_millionth():
    out = resolve.resolve(0, 0.083333, _p(size_mult=0.5), 0.5,
                          fractional=True)
    assert out["final_shares"] == 0.041666
    assert out["decision_maker"] == "agent"


def test_resolve_whole_share_floor_unchanged():
    out = resolve.resolve(0, 10, _p(size_mult=0.55), 0.5)
    assert out["final_shares"] == 5


def test_resolve_fractional_fallthrough_keeps_size_hi():
    out = resolve.resolve(0, 0.083333, None, 0.5, fractional=True)
    assert out["final_shares"] == 0.083333
