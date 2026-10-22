import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _ask(question):
    entries = load_entries(JARGON_JSON)
    df = load_cases(CASES_CSV)
    return chat.answer(question, df, build_patterns(entries), entries, history=[])


def test_what_happened_with_a_case_returns_its_card():
    reply = _ask("what happened in CS-2026-1047?")
    assert reply["kind"] == "cases"
    assert reply["case_ids"] == ["CS-2026-1047"]


def test_what_happened_does_not_fall_through_to_glossary_refusal():
    reply = _ask("what happened in CS-2026-1047?")
    assert "not in the glossary" not in reply["text"]


def test_jargon_question_still_answers_from_glossary():
    reply = _ask("what is LTV?")
    assert "Loan-to-Value" in reply["text"]
