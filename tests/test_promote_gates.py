import pytest

from pipeline.promote import catalog, gates

CFG = catalog.DEFAULT_CONFIG


def _lead(**over):
    lead = {"instrument": "GLD", "instrument_kind": "etf",
            "signal": "cot_commercial_extreme", "direction": "long",
            "horizon_band": "weeks", "score": 95.0, "rank_pct": None,
            "as_of_date": "2026-06-30",
            "details": '{"asset_class":"metals"}'}
    lead.update(over)
    return lead


def _group(**over):
    g = {"instrument": "GLD", "instrument_kind": "etf", "direction": "long",
         "det_score": 0.95, "horizon_band": "weeks",
         "as_of_date": "2026-06-30",
         "signals": [{"signal": "cot_commercial_extreme", "det_score": 0.95,
                      "as_of_date": "2026-06-30"}],
         "details": [{"asset_class": "metals"}]}
    g.update(over)
    return g


def test_det_score_directional_extremity():
    assert gates.normalize_det_score(_lead(score=95.0)) == pytest.approx(0.95)
    # short at COT index 5 scores 0.95 — shorts compete on equal footing
    assert gates.normalize_det_score(
        _lead(direction="short", score=5.0)) == pytest.approx(0.95)
    assert gates.normalize_det_score(_lead(
        signal="quality_composite", instrument_kind="stock",
        rank_pct=0.97, score=1.8)) == pytest.approx(0.97)
    assert gates.normalize_det_score(_lead(
        signal="quality_composite", direction="short",
        rank_pct=0.03, score=-1.8)) == pytest.approx(0.97)
    assert gates.normalize_det_score(_lead(signal="mystery")) is None


def test_det_score_null_score_is_none_not_max_extremity():
    # a NULL COT score must normalize to None, not 1.0 (max extremity), even
    # on a short (which would otherwise flip 0.0 -> 1.0 via `1.0 - frac`).
    assert gates.normalize_det_score(_lead(score=None, direction="short")) is None


def test_group_leads_dedups_and_averages():
    leads = [_lead(), _lead(score=85.0, as_of_date="2026-07-01",
                            horizon_band="months"),
             _lead(instrument="SLV", score=97.0)]
    groups, rejections = gates.group_leads(leads)
    assert rejections == []
    by_inst = {g["instrument"]: g for g in groups}
    gld = by_inst["GLD"]
    assert gld["det_score"] == pytest.approx((0.95 + 0.85) / 2)  # 1/N mean
    assert gld["horizon_band"] == "months"                       # longest wins
    assert gld["as_of_date"] == "2026-07-01"                     # max member
    assert len(gld["signals"]) == 2


def test_group_leads_rejects_unnormalizable():
    groups, rejections = gates.group_leads([_lead(signal="mystery")])
    assert groups == []
    assert rejections[0]["gate"] == "data_missing"


def test_gate_direction_default_rejects_shorts():
    groups = [_group(), _group(instrument="SPY", direction="short")]
    passed, rej = gates.gate_direction(groups, allow_short=False)
    assert [g["instrument"] for g in passed] == ["GLD"]
    assert rej[0]["gate"] == "direction"
    passed2, rej2 = gates.gate_direction(groups, allow_short=True)
    assert len(passed2) == 2 and rej2 == []


def test_gate_liquidity_floors_and_data_missing():
    liq = {"etf": {"GLD": {"price": 200.0, "averageVolume": 5e6,
                           "dollarVolume": 1e9, "atr": 4.0},
                   "SOYB": {"price": 22.0, "averageVolume": 6e4,
                            "dollarVolume": 1.1e6, "atr": 0.3}},
           "stock": {"AAA": {"price": 3.0, "averageVolume": 1e6,
                             "dollarVolume": 3e6, "atr": 0.2,
                             "sector": "Tech", "nextEarningsDate": None}}}
    groups = [_group(),
              _group(instrument="SOYB"),                 # $1.1M < $10M floor
              _group(instrument="AAA", instrument_kind="stock",
                     details=[{}]),                      # price 3 < 5
              _group(instrument="GONE")]                 # no liquidity row
    passed, rej = gates.gate_liquidity(groups, liq, CFG)
    assert [g["instrument"] for g in passed] == ["GLD"]
    assert passed[0]["price"] == 200.0
    assert passed[0]["sector"] == "metals"               # ETF: asset_class
    assert passed[0]["next_earnings_date"] is None
    by_inst = {r["instrument"]: r for r in rej}
    assert by_inst["SOYB"]["gate"] == "liquidity"
    assert by_inst["AAA"]["gate"] == "liquidity"
    assert by_inst["GONE"]["gate"] == "data_missing"


def test_gate_confluence_two_signals_or_strong_extreme():
    weak_single = _group(instrument="MID", det_score=0.80)
    strong_single = _group(det_score=0.96)
    multi = _group(instrument="TWO", det_score=0.70,
                   signals=[{"signal": "a", "det_score": 0.7,
                             "as_of_date": "2026-06-30"},
                            {"signal": "b", "det_score": 0.7,
                             "as_of_date": "2026-06-30"}])
    passed, rej = gates.gate_confluence([weak_single, strong_single, multi], CFG)
    assert {g["instrument"] for g in passed} == {"GLD", "TWO"}
    assert rej[0]["instrument"] == "MID" and rej[0]["gate"] == "confluence"


def test_gate_confluence_rejects_repeated_same_signal():
    # Two members but the SAME signal (e.g. two cot_commercial_extreme rows
    # for the same instrument from different as_of_dates) — not distinct,
    # so this must NOT qualify for the multi-signal arm.
    repeated = _group(instrument="DUP", det_score=0.80,
                      signals=[{"signal": "cot_commercial_extreme",
                                "det_score": 0.85, "as_of_date": "2026-06-23"},
                               {"signal": "cot_commercial_extreme",
                                "det_score": 0.75, "as_of_date": "2026-06-30"}])
    passed, rej = gates.gate_confluence([repeated], CFG)
    assert passed == []
    assert rej[0]["instrument"] == "DUP" and rej[0]["gate"] == "confluence"


def test_gate_sector_cap_keeps_top_two_deterministic():
    groups = [_group(instrument=i, det_score=s, sector="metals")
              for i, s in (("GLD", 0.99), ("SLV", 0.97), ("CPER", 0.96))]
    groups.append(_group(instrument="SPY", det_score=0.95,
                         sector="equity_index"))
    passed, rej = gates.gate_sector_cap(groups, CFG)
    assert {g["instrument"] for g in passed} == {"GLD", "SLV", "SPY"}
    assert rej[0]["instrument"] == "CPER" and rej[0]["gate"] == "sector_cap"


def test_gate_max_positions_top_n_by_score():
    groups = [_group(instrument=f"E{i:02d}", det_score=0.90 + i / 1000,
                     sector=f"s{i}") for i in range(12)]
    passed, rej = gates.gate_max_positions(groups, CFG)
    assert len(passed) == 10
    assert {r["instrument"] for r in rej} == {"E00", "E01"}   # lowest scores
    assert all(r["gate"] == "max_positions" for r in rej)


def test_size_candidate_hand_computed_with_adv_cap():
    # equity 100k, risk 1%, regime 1.0 -> risk_dollars 1000; atr 2 * mult 2
    # -> stop_distance 4; floor(1000/4)=250 shares; ADV cap 0.01*10_000=100
    # -> shares 100; realized_risk 400 < 1000; stop 50-4=46
    g = _group(price=50.0, atr=2.0, sector="metals",
               next_earnings_date=None, average_volume=10_000.0,
               dollar_volume=5e8)
    cand, rej = gates.size_candidate(g, equity=100_000.0, regime_scalar=1.0,
                                     cfg=CFG)
    assert rej is None
    assert cand["shares"] == 100
    assert cand["stop_price"] == pytest.approx(46.0)
    assert cand["stop_distance"] == pytest.approx(4.0)
    assert cand["risk_dollars"] == pytest.approx(1000.0)
    assert cand["realized_risk"] == pytest.approx(400.0)
    assert (cand["size_lo"], cand["size_hi"]) == (0, 100)


def test_size_candidate_regime_scalar_halves_risk():
    g = _group(price=50.0, atr=2.0, sector="metals",
               next_earnings_date=None, average_volume=1e9,
               dollar_volume=5e8)
    cand, _ = gates.size_candidate(g, equity=100_000.0, regime_scalar=0.5,
                                   cfg=CFG)
    assert cand["risk_dollars"] == pytest.approx(500.0)
    assert cand["shares"] == 125                        # floor(500/4)


def test_size_candidate_short_stop_above_price():
    g = _group(direction="short", price=50.0, atr=2.0, sector="metals",
               next_earnings_date=None, average_volume=1e9, dollar_volume=5e8)
    cand, _ = gates.size_candidate(g, equity=100_000.0, regime_scalar=1.0,
                                   cfg=CFG)
    assert cand["stop_price"] == pytest.approx(54.0)


def test_size_candidate_zero_shares_rejected():
    g = _group(price=50.0, atr=2.0, sector="metals",
               next_earnings_date=None, average_volume=10.0,  # cap -> 0
               dollar_volume=5e8)
    cand, rej = gates.size_candidate(g, equity=100_000.0, regime_scalar=1.0,
                                     cfg=CFG)
    assert cand is None and rej["gate"] == "size_zero"
    # degenerate atr -> no stop distance -> size_zero too
    g2 = _group(price=50.0, atr=0.0, sector="m", next_earnings_date=None,
                average_volume=1e9, dollar_volume=5e8)
    cand2, rej2 = gates.size_candidate(g2, equity=100_000.0, regime_scalar=1.0,
                                       cfg=CFG)
    assert cand2 is None and rej2["gate"] == "size_zero"


# --- fractional sizing + notional-cost checks (DEFENSES_ROADMAP) ---

def _sized_group(**over):
    g = _group(price=310.0, atr=6.0, sector="gold", next_earnings_date=None,
               average_volume=5_000_000.0, dollar_volume=5e8)
    g.update(over)
    return g


def test_size_candidate_fractional_small_account():
    import dataclasses
    import math
    cfg = dataclasses.replace(CFG, fractional_shares=True)
    # $200.37 equity, risk-off 0.5 -> risk ~$1.00; stop 12 -> ~0.0834 shares
    cand, rej = gates.size_candidate(_sized_group(), equity=200.37,
                                     regime_scalar=0.5, cfg=cfg)
    assert rej is None
    expected = math.floor((200.37 * 0.01 * 0.5) / 12.0 * 1e6 + 1e-6) / 1e6
    assert cand["shares"] == expected
    assert 0 < cand["shares"] < 1
    assert cand["size_hi"] == cand["shares"]
    assert cand["realized_risk"] == pytest.approx(cand["shares"] * 12.0)


def test_size_candidate_whole_share_notional_clamp():
    # 1 GLD share $310 > $200 equity: even with a huge risk budget the
    # notional clamp zeroes it in whole-share mode -> 'notional' rejection
    import dataclasses
    cfg = dataclasses.replace(CFG, risk_fraction=2.0)
    cand, rej = gates.size_candidate(_sized_group(), equity=200.0,
                                     regime_scalar=1.0, cfg=cfg)
    assert cand is None and rej["gate"] == "notional"


def test_size_candidate_fractional_notional_clamp_caps_at_equity():
    import dataclasses
    cfg = dataclasses.replace(CFG, fractional_shares=True, risk_fraction=2.0)
    cand, rej = gates.size_candidate(_sized_group(), equity=200.0,
                                     regime_scalar=1.0, cfg=cfg)
    assert rej is None
    assert cand["shares"] * 310.0 <= 200.0


def test_size_candidate_fractional_min_notional():
    # shares worth < $1 -> rejected as dust, not ordered
    import dataclasses
    cfg = dataclasses.replace(CFG, fractional_shares=True)
    cand, rej = gates.size_candidate(_sized_group(), equity=2.0,
                                     regime_scalar=1.0, cfg=cfg)
    assert cand is None and rej["gate"] == "notional"


def test_size_candidate_whole_share_default_unchanged():
    # regression: default config on a comfortable account is byte-identical
    g = _sized_group(price=50.0, atr=2.0, average_volume=10_000.0)
    cand, rej = gates.size_candidate(g, equity=100_000.0, regime_scalar=1.0,
                                     cfg=CFG)
    assert rej is None
    assert cand["shares"] == 100 and isinstance(cand["shares"], int)


def test_gate_notional_book_cuts_lowest_score_first():
    cands = [{"instrument": "A", "direction": "long", "det_score": 0.9,
              "shares": 0.5, "price": 300.0},
             {"instrument": "B", "direction": "long", "det_score": 0.8,
              "shares": 0.4, "price": 300.0}]
    passed, rejections = gates.gate_notional_book(cands, 200.0)
    assert [c["instrument"] for c in passed] == ["A"]
    assert rejections[0]["gate"] == "notional"
    assert rejections[0]["instrument"] == "B"


def test_gate_notional_book_all_fit_no_cuts():
    cands = [{"instrument": "A", "direction": "long", "det_score": 0.9,
              "shares": 0.1, "price": 300.0}]
    passed, rejections = gates.gate_notional_book(cands, 200.0)
    assert passed == cands and rejections == []


# --- crowding gate (DEFENSES_ROADMAP Tier 1 + 2) ---

def _crowd(rank=2, mentions=90, mean=10.0, std=2.0, n=10, ticker="GLD"):
    return {ticker: {"rank": rank, "mentions": mentions,
                     "baseline_mean": mean, "baseline_std": std, "n": n}}


def test_gate_crowding_kills_hot_name():
    passed, rej = gates.gate_crowding([_sized_group()], _crowd(), CFG)
    assert passed == [] and rej[0]["gate"] == "crowding"
    assert "rank 2" in rej[0]["reason"]


def test_gate_crowding_rank_alone_not_enough():
    # top-rank but only 1.5x its own norm (an always-chattered name)
    passed, rej = gates.gate_crowding(
        [_sized_group()], _crowd(rank=1, mentions=15), CFG)
    assert len(passed) == 1 and rej == []


def test_gate_crowding_mentions_spike_alone_not_enough():
    # 9x its norm but nowhere near the top of the board
    passed, rej = gates.gate_crowding(
        [_sized_group()], _crowd(rank=40, mentions=90), CFG)
    assert len(passed) == 1 and rej == []


def test_gate_crowding_absent_name_passes_free():
    passed, rej = gates.gate_crowding([_sized_group()], {}, CFG)
    assert len(passed) == 1 and rej == []
    assert all("retail_attention_z" not in d for d in passed[0]["details"])


def test_gate_crowding_thin_baseline_passes():
    passed, rej = gates.gate_crowding(
        [_sized_group()], _crowd(n=CFG.crowding_min_n - 1), CFG)
    assert len(passed) == 1 and rej == []


def test_gate_crowding_appends_attention_z_detail():
    passed, _ = gates.gate_crowding(
        [_sized_group()], _crowd(rank=40, mentions=14), CFG)
    assert {"retail_attention_z": 2.0} in passed[0]["details"]


def test_gate_crowding_zero_std_no_z_detail():
    passed, _ = gates.gate_crowding(
        [_sized_group()], _crowd(rank=40, mentions=14, std=0.0), CFG)
    assert all("retail_attention_z" not in d for d in passed[0]["details"])
