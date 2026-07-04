from pipeline.gate import catalog


def test_constants_pin_the_spec():
    assert catalog.TAU == 0.5
    assert catalog.HEAT_CAP == 0.06
    assert catalog.DEFAULT_MODEL == "claude-sonnet-5"
    assert catalog.LLM_ATTEMPTS == 3
    assert catalog.RATIONALE_MAX == 500
    assert "cik" not in catalog.MASK_DETAIL_KEYS
    assert "commercial_index" in catalog.MASK_DETAIL_KEYS


def test_system_prompt_states_grammar_and_caution_scope():
    sp = catalog.SYSTEM_PROMPT
    for token in ('"action"', '"size_mult"', '"confidence"', '"rationale"',
                  "approve", "veto", "caution", "logged"):
        assert token in sp, token
    assert "never increase" in sp.lower()


def test_guardrail_config_version_sensitive_to_every_input():
    base = catalog.guardrail_config_version(0.5, 0.06, "claude-sonnet-5", "c" * 64)
    assert len(base) == 64
    assert base == catalog.guardrail_config_version(0.5, 0.06,
                                                    "claude-sonnet-5", "c" * 64)
    for variant in (
            catalog.guardrail_config_version(0.7, 0.06, "claude-sonnet-5", "c" * 64),
            catalog.guardrail_config_version(0.5, 0.05, "claude-sonnet-5", "c" * 64),
            catalog.guardrail_config_version(0.5, 0.06, "other-model", "c" * 64),
            catalog.guardrail_config_version(0.5, 0.06, "claude-sonnet-5", "d" * 64)):
        assert variant != base
