import re

import case_facts
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases

NAN_WORD = re.compile(r"\b(nan|none|nat)\b", re.I)


def test_unreached_stage_is_reported_without_nan():
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))
    # CS-2026-1012 has no Stage 3 timestamp in the CSV
    text = case_facts.answer_facts("how long did CS-2026-1012 take to reach stage 3", "CS-2026-1012", df, patterns)
    assert text is not None
    assert "has not been reached yet" in text
    assert not NAN_WORD.search(text)


def test_reached_stage_still_gives_hours():
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))
    text = case_facts.answer_facts("how long did CS-2026-1001 take to reach stage 3", "CS-2026-1001", df, patterns)
    assert "hours" in text
    assert not NAN_WORD.search(text)
