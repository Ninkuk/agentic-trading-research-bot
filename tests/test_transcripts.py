import pytest

from tools.research.transcripts import (
    MANAGEMENT,
    OUTSIDE,
    UNATTRIBUTED,
    classify_side,
    flatten_turn,
    issuer_from_turns,
)

VZ_LONG = "Verizon Communications Inc."


def turn(company: object, role: object = None, text: str = "hi") -> dict:
    return {
        "speakerName": "X",
        "role": role,
        "company": company,
        "paragraphs": [[{"text": text, "startSec": 0.0, "endSec": 1.0}]],
    }


def test_flatten_joins_sentences_within_a_paragraph() -> None:
    t = {"paragraphs": [[{"text": "We took share."}, {"text": "A lot of it."}]]}
    assert flatten_turn(t) == "We took share. A lot of it."


def test_flatten_separates_paragraphs() -> None:
    t = {"paragraphs": [[{"text": "One."}], [{"text": "Two."}]]}
    assert flatten_turn(t) == "One.\n\nTwo."


def test_flatten_tolerates_a_turn_with_no_paragraphs() -> None:
    assert flatten_turn({"speakerName": "Operator"}) == ""


def test_management_is_recognised_despite_a_mislabelled_role() -> None:
    # Verizon Q1 2022: CFO Matt Ellis is tagged role="Analyst". `company` is the truth.
    assert classify_side(turn("Verizon", role="Analyst"), "Verizon") == MANAGEMENT


def test_legal_suffix_variants_are_the_same_issuer() -> None:
    # CROX tags its CEO "Crocs" and its CFO "Crocs, Inc." in the same call.
    assert classify_side(turn("Crocs"), "Crocs, Inc.") == MANAGEMENT
    assert classify_side(turn("Crocs, Inc."), "Crocs") == MANAGEMENT


def test_a_longer_issuer_name_still_matches() -> None:
    assert classify_side(turn("Verizon"), VZ_LONG) == MANAGEMENT


def test_a_sibling_subsidiary_is_still_management() -> None:
    # "verizon communications" neither contains nor is contained by "verizon consumer".
    # 115 real VZ turns by the Consumer Group CEO hang on this.
    assert classify_side(turn("Verizon Consumer Group"), VZ_LONG) == MANAGEMENT
    assert classify_side(turn("Verizon Consumer"), VZ_LONG) == MANAGEMENT


def test_a_concatenated_issuer_name_matches_the_spaced_one() -> None:
    assert classify_side(turn("ExxonMobil"), "Exxon Mobil Corporation") == MANAGEMENT


def test_an_outside_firm_is_not_management() -> None:
    goldman = turn("Goldman Sachs", role="MD - Global Investment Research")
    assert classify_side(goldman, "Verizon") == OUTSIDE


def test_jpmorgan_is_not_morgan_stanley() -> None:
    # "morgan" is a substring of "jpmorgan"; it is not a prefix of it. Match on prefix.
    assert classify_side(turn("JPMorgan"), "Morgan Stanley") == OUTSIDE
    assert classify_side(turn("J.P. Morgan"), "Morgan Stanley") == OUTSIDE


def test_morgan_stanley_is_management_only_on_its_own_call() -> None:
    ms = turn("Morgan Stanley")
    assert classify_side(ms, "Morgan Stanley") == MANAGEMENT
    assert classify_side(ms, "Verizon") == OUTSIDE


def test_operator_turns_are_unattributed_even_though_role_is_set() -> None:
    # 14 VZ turns carry role="Operator" with company=None. Never key on `role is None`.
    assert classify_side(turn(None, role="Operator"), "Verizon") == UNATTRIBUTED


def test_null_role_and_null_company_is_unattributed() -> None:
    assert classify_side(turn(None, role=None), "Verizon") == UNATTRIBUTED


def test_blank_company_is_unattributed() -> None:
    assert classify_side(turn("   "), "Verizon") == UNATTRIBUTED


def test_classify_requires_a_non_empty_issuer() -> None:
    with pytest.raises(ValueError, match="issuer"):
        classify_side(turn("Verizon"), "")


def test_issuer_from_turns_picks_the_modal_company() -> None:
    turns = [turn("Verizon"), turn("Verizon"), turn("Morgan Stanley"), turn(None)]
    assert issuer_from_turns(turns) == "Verizon"


def test_issuer_from_turns_is_none_when_nobody_is_attributed() -> None:
    assert issuer_from_turns([turn(None), turn("  ")]) is None
