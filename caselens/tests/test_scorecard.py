import audit_view
import scorecard
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def test_scorecard_has_all_targets_and_no_invented_definitions():
    entries = load_entries(JARGON_JSON)
    patterns = build_patterns(entries)
    df = load_cases(CASES_CSV)
    board = scorecard.build(df, patterns, audit_view.load_log(), entries)
    assert len(board) == 5
    invented = board[board["Target"].str.startswith("Invented")].iloc[0]
    assert invented["Result"] == "pass", invented["Basis"]
    grounding = board[board["Target"].str.startswith("Grounding")].iloc[0]
    assert grounding["Result"] == "pass", grounding["Basis"]
