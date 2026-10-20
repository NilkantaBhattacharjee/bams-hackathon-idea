import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _ask(question):
    entries = load_entries(JARGON_JSON)
    df = load_cases(CASES_CSV)
    return chat.answer(question, df, build_patterns(entries), entries, history=[])["text"]


def test_open_reason_is_specific_not_a_summary():
    text = _ask("What is the reason for this case to be in open status - CS-2026-1005")
    assert "is open because" in text
    assert "Case: CS-2026-1005" not in text
    assert "Key Events" not in text


def test_open_reason_mentions_pending_document():
    text = _ask("Why is CS-2026-1005 still open?")
    assert "Transfer Form" in text


def test_closed_case_reason_says_it_is_closed():
    text = _ask("Why is CS-2026-1001 open?")
    assert "is closed, so it is not open" in text
