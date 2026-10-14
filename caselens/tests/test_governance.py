import pandas as pd

import validate


def _frame(**overrides):
    row = {
        "Case_ID": ["CS-1", "CS-2"],
        "Client_Email": ["a@example.com", "b@example.com"],
        "Priority": ["P1", "P2"],
        "Case_Status": ["Closed", "Open"],
        "Stage_5_Timestamp": [pd.Timestamp("2026-03-01"), pd.NaT],
    }
    row.update(overrides)
    return pd.DataFrame(row)


def test_clean_data_has_no_governance_issues():
    assert validate.find_governance_issues(_frame()).empty


def test_duplicate_email_is_flagged_for_both_cases():
    df = _frame(Client_Email=["same@example.com", "SAME@example.com"])
    issues = validate.find_governance_issues(df)
    assert set(issues.loc[issues["Check"] == "duplicate_email", "Case_ID"]) == {"CS-1", "CS-2"}


def test_missing_priority_is_flagged():
    df = _frame(Priority=["P1", ""])
    issues = validate.find_governance_issues(df)
    assert list(issues.loc[issues["Check"] == "missing_priority", "Case_ID"]) == ["CS-2"]


def test_open_case_with_stage5_timestamp_is_flagged():
    df = _frame(Stage_5_Timestamp=[pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-02")])
    issues = validate.find_governance_issues(df)
    assert list(issues.loc[issues["Check"] == "open_with_stage5", "Case_ID"]) == ["CS-2"]


def test_closed_case_without_stage5_timestamp_is_flagged():
    df = _frame(Stage_5_Timestamp=[pd.NaT, pd.NaT])
    issues = validate.find_governance_issues(df)
    assert list(issues.loc[issues["Check"] == "closed_without_stage5", "Case_ID"]) == ["CS-1"]


def test_real_dataset_governance_report_runs():
    from config import CASES_CSV
    from metrics import load_cases

    issues = validate.find_governance_issues(load_cases(CASES_CSV))
    assert list(issues.columns) == ["Case_ID", "Check", "Detail"]
