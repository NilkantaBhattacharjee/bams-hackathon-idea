import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _ask(question):
    entries = load_entries(JARGON_JSON)
    df = load_cases(CASES_CSV)
    return chat.answer(question, df, build_patterns(entries), entries, history=[])["text"]


def test_total_number_of_cases():
    assert _ask("What is the total number of cases?").startswith("There are 500 cases in total")


def test_total_with_filter_is_not_treated_as_total():
    assert "There are 500 cases in total" not in _ask("How many cases are in stalled status?")


def test_shortest_time_to_close_lists_fastest_first():
    text = _ask("Which case took the shortest time to close?")
    assert text.startswith("Closed cases with the shortest turnaround")
    rows = [line for line in text.splitlines() if line.startswith("- CS-")]
    assert len(rows) == 5


def test_average_turnaround_shows_figure():
    assert "avg turnaround" in _ask("What is the average turnaround?")
