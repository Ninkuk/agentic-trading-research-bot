from sources.screeners.stock_analysis_screener.typing import STRING_IDS, column_type, infer_affinity


def test_infer_real_when_all_numbers():
    assert infer_affinity([1, 2.5, None]) == "REAL"


def test_infer_text_when_any_string():
    assert infer_affinity([1, "x"]) == "TEXT"


def test_infer_text_when_all_null():
    assert infer_affinity([None, None]) == "TEXT"


def test_infer_text_for_bool_values():
    assert infer_affinity([True, False]) == "TEXT"


def test_column_type_respects_string_override():
    # 'cik' is an identifier that can look numeric but must stay TEXT
    assert "cik" in STRING_IDS
    assert column_type("cik", [12345]) == "TEXT"


def test_column_type_infers_numeric():
    assert column_type("price", [10.0, 11.5]) == "REAL"


def test_column_type_date_is_text():
    assert column_type("nextEarningsDate", ["2026-10-16"]) == "TEXT"


def test_yes_no_flags_are_pinned_to_text():
    """STRING_IDS exists so a flag column cannot silently change affinity when
    the feed switches encoding. isPrimaryListing was missing from it while its
    siblings isSpac/optionable were pinned — and composite's stocks_rsi signal
    plus the candidates screen both compare it, so an inferred REAL affinity
    would change what those predicates match without erroring."""
    for flag in ("isSpac", "optionable", "isPrimaryListing"):
        assert flag in STRING_IDS, flag
        assert column_type(flag, [1, 0]) == "TEXT", flag
