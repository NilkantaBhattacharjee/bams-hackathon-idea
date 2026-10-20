import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _ask(question):
    entries = load_entries(JARGON_JSON)
    df = load_cases(CASES_CSV)
    return chat.answer(question, df, build_patterns(entries), entries, history=[])["text"]


def test_why_stalled_answers_with_stall_stages_not_open_status():
    text = _ask("Why was CS-2026-1002 stalled?")
    assert "was stalled in" in text
    assert "Stage 2" in text
    assert "is closed, so it is not open" not in text


def test_why_stalled_with_no_stall_says_so():
    text = _ask("Why was CS-2026-1001 stalled?")
    assert text.startswith("No stall was recorded")


def test_open_reason_question_still_uses_open_rule():
    text = _ask("Why is CS-2026-1005 still open?")
    assert "is open because" in text
