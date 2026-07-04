import json

from pipeline.gate import catalog, mask

NOW = "2026-07-04T20:00:00+00:00"


def _row(**over):
    row = {"instrument": "GLD", "instrument_kind": "etf", "direction": "long",
           "det_score": 0.96, "horizon_band": "weeks",
           "signals": '[{"signal":"cot_commercial_extreme","det_score":0.96,'
                      '"as_of_date":"2026-06-30"}]',
           "price": 200.0, "atr": 4.0, "sector": "metals",
           "next_earnings_date": None, "shares": 125, "stop_price": 192.0,
           "stop_distance": 8.0, "risk_dollars": 1000.0, "realized_risk": 1000.0,
           "size_lo": 0, "size_hi": 125, "as_of_date": "2026-06-30",
           "details": '[{"asset_class":"metals","commercial_index":96.0,'
                      '"speculator_index":12.0,"code":"088691",'
                      '"family":"disaggregated","cik":1234567}]',
           "equity": 100000.0, "regime_scalar": 1.0, "config_hash": "c" * 64}
    row.update(over)
    return row


def test_build_mask_is_deterministic():
    assert mask.build_mask(["SPY", "GLD"]) == {"GLD": "CAND_A", "SPY": "CAND_B"}


def test_masked_view_whitelist_and_derived_fields():
    view = mask.masked_view(mask.parse_input_row(_row()), "CAND_A", NOW)
    assert view["alias"] == "CAND_A"
    assert view["atr_pct"] == round(4.0 / 200.0, 4)
    assert "days_to_earnings" not in view          # NULL earnings -> omitted
    assert view["metrics"] == {"commercial_index": 96.0,
                               "speculator_index": 12.0}
    assert view["signals"] == [{"signal": "cot_commercial_extreme",
                                "det_score": 0.96}]
    rendered = json.dumps(view)
    for leaked in ("GLD", "088691", "200.0", "192.0", "2026-06-30", "cik"):
        assert leaked not in rendered, leaked


def test_days_to_earnings_relative_and_past_omitted():
    row = mask.parse_input_row(_row(instrument_kind="stock",
                                    next_earnings_date="2026-07-16"))
    view = mask.masked_view(row, "CAND_A", NOW)
    assert view["days_to_earnings"] == 12
    past = mask.masked_view(mask.parse_input_row(
        _row(next_earnings_date="2026-07-01")), "CAND_A", NOW)
    assert "days_to_earnings" not in past


def test_render_prompt_leak_regression():
    view = mask.masked_view(mask.parse_input_row(_row()), "CAND_A", NOW)
    user = mask.render_user_prompt(view)
    full = catalog.SYSTEM_PROMPT + user
    for leaked in ("GLD", "Gold", "088691", "200.0", "192.0",
                   "2026-06-30", "2026-07-04"):
        assert leaked not in full, leaked
    assert "CAND_A" in user


def test_hashes_stable_across_ordering_and_reparse():
    a = mask.sha256_canonical({"b": 2, "a": [1, {"y": 1, "x": 0}]})
    b = mask.sha256_canonical({"a": [1, {"x": 0, "y": 1}], "b": 2})
    assert a == b
    # raw-text vs reparsed JSON columns must hash identically once parsed
    r1 = mask.parse_input_row(_row(signals='[{"det_score":0.96,'
                                           '"signal":"cot_commercial_extreme",'
                                           '"as_of_date":"2026-06-30"}]'))
    r2 = mask.parse_input_row(_row())
    assert mask.sha256_canonical(r1) == mask.sha256_canonical(r2)


def test_prompt_hash_binds_system_and_user():
    h1 = mask.prompt_hash("sys", "user")
    assert h1 != mask.prompt_hash("sys", "user2")
    assert h1 != mask.prompt_hash("sys2", "user")
    assert len(h1) == 64
