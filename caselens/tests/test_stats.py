import chat
import stats
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _data():
    entries = load_entries(JARGON_JSON)
    return load_cases(CASES_CSV), entries, build_patterns(entries)


def test_bulk_questions_trigger():
    for q in ["Average turnaround (hours) by type", "Longest stage per case", "Stalled cases (%) by sub-type",
              "Cases by type", "Stalled cases (%) by type"]:
        assert stats.triggers(q), q


def test_single_case_and_count_questions_do_not_trigger():
    for q in ["How many cases are in stalled status?", "Why was CS-2026-1006 stalled?",
              "Average turnaround of CS-2026-1001"]:
        assert not stats.triggers(q), q


def test_type_counts_add_up_to_all_cases():
    df, _, patterns = _data()
    t = stats.case_table(df, patterns)
    by_type = stats.group_table(t, "Type")
    assert int(by_type["Cases"].sum()) == len(df)
    assert int(by_type["Stalled"].sum()) == int(t["Stalled"].sum())


def test_average_turnaround_uses_closed_cases_only():
    df, _, patterns = _data()
    t = stats.case_table(df, patterns)
    by_sub = stats.group_table(t, "Sub_type")
    sub = by_sub.iloc[0]["Sub_type"]
    closed = t[(t["Sub_type"] == sub) & t["Closed"] & t["TAT"].notna()]
    assert abs(by_sub.iloc[0]["Avg_TAT_hours"] - round(closed["TAT"].mean(), 1)) < 0.05


def test_chat_answers_stalled_percent_by_sub_type():
    df, entries, patterns = _data()
    text = chat.answer("Stalled cases (%) by sub-type", df, patterns, entries, history=[])["text"]
    assert "Fraud Dispute" in text
    assert "%" in text


def test_chat_answers_longest_stage_per_case():
    df, entries, patterns = _data()
    text = chat.answer("Longest stage per case", df, patterns, entries, history=[])["text"]
    assert text.startswith("Longest stage per case")
