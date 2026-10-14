import pytest

from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, comments_without_match, explain_comments, find_terms, load_entries
from metrics import load_cases


@pytest.fixture(scope="module")
def patterns():
    return build_patterns(load_entries(JARGON_JSON))


@pytest.fixture(scope="module")
def real_cases():
    return load_cases(CASES_CSV)


def ids(text, patterns):
    return {hit["ID"] for hit in find_terms(text, patterns)}


def test_abbreviations_match_with_dictionary_ids(patterns):
    # KYC is JD-004, AML is JD-022
    assert ids("KYC/AML verified.", patterns) == {"JD-004", "JD-022"}


def test_full_form_matches_to_same_id(patterns):
    # "Credit Committee" is the full form of CC (JD-008)
    assert ids("Credit Committee approval granted.", patterns) == {"JD-008"}


def test_hyphenated_code_matches(patterns):
    # DE-4 is JD-025
    assert ids("Auto-approved by decision engine rule DE-4.", patterns) == {"JD-025"}


def test_no_match_inside_longer_word(patterns):
    # "IB" must not match inside "IBM"
    assert ids("IBM statement received.", patterns) == set()


def test_unknown_phrases_are_not_guessed(patterns):
    assert ids("Credit check passed. Credit OK.", patterns) == set()


def test_each_term_reported_once(patterns):
    hits = find_terms("LTV exceeds 80%. LTV recalculated.", patterns)
    assert [h["ID"] for h in hits] == ["JD-007"]


def test_stage2_comment_of_case_1001(real_cases, patterns):
    matches = explain_comments(real_cases, patterns)
    stage2 = matches[(matches.Case_ID == "CS-2026-1001") & (matches.Stage == 2)]
    assert set(stage2.ID) == {"JD-004", "JD-005", "JD-006"}  # KYC, PEP, SAN


def test_stage3_comment_of_case_1001(real_cases, patterns):
    matches = explain_comments(real_cases, patterns)
    stage3 = matches[(matches.Case_ID == "CS-2026-1001") & (matches.Stage == 3)]
    assert set(stage3.ID) == {"JD-007", "JD-008", "JD-009"}  # LTV, CC, DTI


def test_every_hit_has_an_explanation(real_cases, patterns):
    matches = explain_comments(real_cases, patterns)
    assert not matches.empty
    assert matches.Plain_English_Explanation.str.strip().ne("").all()


def test_comments_without_terms_are_listed(real_cases, patterns):
    gaps = comments_without_match(real_cases, patterns)
    # Stage 1 of CS-2026-1001 has "Case logged via IB" which matches, so it must not be a gap
    assert not ((gaps.Case_ID == "CS-2026-1001") & (gaps.Stage == 1)).any()
