import re

import pytest

from tools.research.transcripts import (
    LEXICON,
    MANAGEMENT,
    OUTSIDE,
    UNATTRIBUTED,
    ConceptStat,
    Coverage,
    classify_side,
    coverage,
    flatten_turn,
    issuer_from_turns,
    scan_concepts,
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


def test_issuer_from_turns_is_unreliable_on_a_single_conference_call() -> None:
    # A conference presentation is 1:1 (one bank moderator, one executive), so the
    # host bank can tie management on turn count within that single call. Verizon's
    # 2026-05-18 JPMorgan conference ties 19-19; `most_common` breaks the tie by
    # first-seen insertion order, so whichever name appears first in `turns` wins —
    # not necessarily the real issuer. Electing an issuer from one call is unsafe;
    # this test pins that hazard so a "fix" that makes it look safe fails loudly.
    conference_turns = [turn("JPMorgan")] * 19 + [turn("Verizon")] * 19
    assert issuer_from_turns(conference_turns) == "JPMorgan"


def test_issuer_from_turns_tie_breaks_by_first_seen_insertion_order() -> None:
    # Same tie, opposite insertion order: the winner flips. This is the arbitrary
    # part — assert it explicitly so nobody mistakes the tie-break for a signal.
    conference_turns = [turn("Verizon")] * 19 + [turn("JPMorgan")] * 19
    assert issuer_from_turns(conference_turns) == "Verizon"


def test_pooling_calls_before_electing_the_issuer_finds_the_real_issuer() -> None:
    # The supported usage: pool turns from many calls (a tied conference call plus
    # an earnings call, where management dominates) before calling
    # `issuer_from_turns`. Pooled, the issuer wins outright.
    conference_turns = [turn("JPMorgan")] * 19 + [turn("Verizon")] * 19
    earnings_turns = [turn("Verizon")] * 40 + [turn("Morgan Stanley")] * 5
    pooled = conference_turns + earnings_turns
    assert issuer_from_turns(pooled) == "Verizon"


def index(*dates: str) -> list[dict]:
    return [{"eventDate": d, "quarterLabel": "Q1", "detailSlug": f"s-{d}"} for d in dates]


def test_coverage_reports_span_and_count() -> None:
    cov = coverage(index("2021-03-12", "2026-06-09", "2023-01-01"))
    assert cov.n_calls == 3
    assert cov.first == "2021-03-12"
    assert cov.last == "2026-06-09"


def test_coverage_of_an_empty_index_is_not_an_error() -> None:
    # BABA, TSM, SAP, SONY have no corpus at all. This is a normal outcome.
    cov = coverage([])
    assert cov == Coverage(n_calls=0, first=None, last=None, ipo_date=None, uncovered_years=None)


def test_uncovered_years_measures_the_gap_from_ipo_to_first_call() -> None:
    # AT&T: 12 calls from 2021, but listed long before.
    cov = coverage(index("2021-03-12"), ipo_date="1983-11-21")
    assert cov.uncovered_years == pytest.approx(37.3, abs=0.1)


def test_uncovered_years_is_none_without_an_ipo_date() -> None:
    assert coverage(index("2021-03-12")).uncovered_years is None


def test_uncovered_years_is_zero_when_coverage_predates_the_ipo() -> None:
    # Never report a negative gap; clamp at zero.
    cov = coverage(index("2010-05-13"), ipo_date="2012-01-01")
    assert cov.uncovered_years == 0.0


def test_uncovered_years_is_none_when_the_index_is_empty() -> None:
    assert coverage([], ipo_date="1983-11-21").uncovered_years is None


def test_coverage_ignores_rows_with_no_event_date() -> None:
    cov = coverage([{"eventDate": "2024-01-01"}, {"detailSlug": "orphan"}])
    assert cov.n_calls == 2
    assert cov.first == cov.last == "2024-01-01"


def test_coverage_rejects_a_malformed_event_date_without_ipo_date() -> None:
    with pytest.raises(ValueError, match="Jul 10, 2026"):
        coverage([{"eventDate": "Jul 10, 2026"}])


def test_coverage_rejects_a_malformed_event_date_with_ipo_date() -> None:
    with pytest.raises(ValueError, match="Jul 10, 2026"):
        coverage([{"eventDate": "Jul 10, 2026"}], ipo_date="1983-11-21")


def test_coverage_rejects_a_non_zero_padded_date_rather_than_misordering_it() -> None:
    # Raw-string sort would silently put "2024-1-5" after "2024-01-10" (lexicographic
    # '1' > '0'), reporting the wrong `last`. On this repo's Python (3.12.7),
    # date.fromisoformat rejects the non-zero-padded form outright, so the old wrong
    # answer (last == "2024-1-5") is impossible either way: it now raises instead.
    with pytest.raises(ValueError, match="2024-1-5"):
        coverage([{"eventDate": "2024-1-5"}, {"eventDate": "2024-01-10"}])


def test_coverage_skips_an_empty_string_event_date_without_raising() -> None:
    cov = coverage([{"eventDate": ""}, {"eventDate": "2024-01-01"}])
    assert cov.n_calls == 2
    assert cov.first == cov.last == "2024-01-01"


def test_scan_counts_documents_not_hits() -> None:
    # "churn" five times in one call is ONE observation, not five.
    docs = [("2024-01-01", "churn churn churn churn churn")]
    (stat,) = scan_concepts(docs, {"churn": [r"churn"]})
    assert stat.df == 1
    assert stat.n_docs == 1


def test_scan_reports_span_and_distinct_seasons() -> None:
    docs = [
        ("2019-06-18", "we took market share"),
        ("2019-11-01", "market share again"),
        ("2026-05-13", "still taking market share"),
        ("2022-01-01", "nothing relevant here"),
    ]
    (stat,) = scan_concepts(docs, {"market share": [r"market share"]})
    assert stat.df == 3
    assert stat.n_docs == 4
    assert stat.first == "2019-06-18"
    assert stat.last == "2026-05-13"
    assert stat.seasons == 2  # 2019 and 2026 — not 3


def test_scan_reports_a_concept_that_never_appears() -> None:
    # An absent concept must still be reported, with df=0. Silence is the finding.
    docs = [("2024-01-01", "we discuss churn constantly")]
    (stat,) = scan_concepts(docs, {"CAC": [r"\bcac\b", r"customer acquisition cost"]})
    assert stat.df == 0
    assert stat.first is None
    assert stat.last is None
    assert stat.seasons == 0


def test_scan_matches_any_synonym_in_the_set() -> None:
    docs = [("2024-01-01", "our share of wallet is growing")]
    (stat,) = scan_concepts(docs, {"wallet share": [r"share of wallet", r"wallet share"]})
    assert stat.df == 1


def test_scan_is_case_insensitive() -> None:
    docs = [("2024-01-01", "Market Share leadership")]
    (stat,) = scan_concepts(docs, {"market share": [r"market share"]})
    assert stat.df == 1


def test_scan_orders_results_rarest_first() -> None:
    docs = [("2024-01-01", "churn"), ("2025-01-01", "churn and market share")]
    stats = scan_concepts(docs, {"churn": [r"churn"], "market share": [r"market share"]})
    assert [s.concept for s in stats] == ["market share", "churn"]


def test_scan_over_an_empty_corpus_reports_every_concept_as_absent() -> None:
    stats = scan_concepts([], {"churn": [r"churn"]})
    assert stats == [ConceptStat("churn", df=0, n_docs=0, first=None, last=None, seasons=0)]


def test_default_lexicon_covers_the_disclosure_probes() -> None:
    assert "market share" in LEXICON
    assert "we don't disclose" in LEXICON
    assert all(patterns for patterns in LEXICON.values())


def test_default_lexicon_patterns_all_compile() -> None:
    patterns = [p for ps in LEXICON.values() for p in ps]
    compiled = [re.compile(p) for p in patterns]
    assert len(compiled) == len(patterns)


def test_lexicon_separates_market_share_from_wallet_share() -> None:
    # A firm may disclose one and not the other; conflating them hides that.
    docs = [("2024-01-01", "our share of wallet grew")]
    stats = {s.concept: s.df for s in scan_concepts(docs, LEXICON)}
    assert stats["wallet share"] == 1
    assert stats["market share"] == 0
