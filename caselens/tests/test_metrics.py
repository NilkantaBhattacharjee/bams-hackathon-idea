import pandas as pd
import pytest

from config import CASES_CSV, JARGON_JSON
from metrics import load_cases, recalculated_tat_hours, stage_durations, total_tat_hours
from validate import extract_tokens, find_issues, load_terms

HEADER = (
    "Case_ID,Client_ID,Specific_Type,Specific_Sub_Type,"
    "Stage_1_Timestamp,Stage_1_Comments,Stage_2_Timestamp,Stage_2_Comments,"
    "Stage_3_Timestamp,Stage_3_Comments,Stage_4_Timestamp,Stage_4_Comments,"
    "Stage_5_Timestamp,Stage_5_Comments,Total_TAT_Hours,Documents_Attached"
)


def write_csv(tmp_path, rows):
    path = tmp_path / "cases.csv"
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def row(case_id, stamps, tat):
    s1, s2, s3, s4, s5 = stamps
    return (
        f"{case_id},CL-1,Retail_Banking,Personal_Loan,"
        f"{s1},Logged.,{s2},KYC clear.,{s3},DTI ok.,{s4},Approved.,{s5},Disbursed.,{tat},Yes"
    )


@pytest.fixture(scope="module")
def real_cases():
    return load_cases(CASES_CSV)


def test_stage1_duration_for_case_1001(real_cases):
    durations = stage_durations(real_cases)
    stage1 = durations[(durations.Case_ID == "CS-2026-1001") & (durations.Stage == 1)]
    # Stage 1 hours are read from the timestamps, so compare with the source values
    row = real_cases[real_cases.Case_ID == "CS-2026-1001"].iloc[0]
    expected = (row["Stage_2_Timestamp"] - row["Stage_1_Timestamp"]).total_seconds() / 3600
    assert stage1["Hours"].iloc[0] == pytest.approx(expected)


def test_total_tat_uses_stored_value(real_cases):
    tat = total_tat_hours(real_cases)
    value = tat[real_cases.Case_ID == "CS-2026-1001"].iloc[0]
    stored = real_cases.loc[real_cases.Case_ID == "CS-2026-1001", "Total_TAT_Hours"].iloc[0]
    assert value == pytest.approx(stored)


def test_recalculated_tat_matches_stored_for_case_1001(real_cases):
    value = recalculated_tat_hours(real_cases)[real_cases.Case_ID == "CS-2026-1001"].iloc[0]
    # Stage 1 to Stage 5 timestamps, compared with the stored TAT for the same case
    stored = real_cases.loc[real_cases.Case_ID == "CS-2026-1001", "Total_TAT_Hours"].iloc[0]
    assert value == pytest.approx(stored, abs=0.01)  # stored value is rounded to 2 decimals


def test_case_1097_stages_are_in_order(real_cases):
    issues = find_issues(real_cases)
    flagged = issues[(issues.Case_ID == "CS-2026-1097") & (issues.Check == "out_of_order")]
    assert flagged.empty


def test_clean_rows_produce_no_issues(tmp_path):
    path = write_csv(tmp_path, [
        row("CS-1", ["2026-03-01 08:00:00", "2026-03-01 10:00:00", "2026-03-01 12:00:00",
                     "2026-03-02 12:00:00", "2026-03-03 12:00:00"], 52),
    ])
    issues = find_issues(load_cases(path))
    assert issues.empty


def test_stored_tat_mismatch_is_reported(tmp_path):
    path = write_csv(tmp_path, [
        row("CS-2", ["2026-03-01 08:00:00", "2026-03-01 10:00:00", "2026-03-01 12:00:00",
                     "2026-03-02 12:00:00", "2026-03-03 12:00:00"], 40),
    ])
    issues = find_issues(load_cases(path))
    assert list(issues.Check) == ["tat_mismatch"]


def test_missing_timestamp_is_reported(tmp_path):
    path = write_csv(tmp_path, [
        row("CS-3", ["2026-03-01 08:00:00", "", "2026-03-01 12:00:00",
                     "2026-03-02 12:00:00", "2026-03-03 12:00:00"], 52),
    ])
    issues = find_issues(load_cases(path))
    assert "missing_or_invalid_timestamp" in set(issues.Check)


def test_token_extraction_finds_codes_and_ignores_words():
    tokens = extract_tokens("KYC/AML verified. DE-4 applied. Credit OK. P2 set. 3DS check.")
    assert {"KYC", "AML", "DE-4", "P2", "3DS"} <= tokens
    assert "OK" not in tokens
    assert "Credit" not in tokens


def test_dictionary_contains_confusable_codes_from_comments():
    terms = load_terms(JARGON_JSON)
    assert {"KYC", "AML", "DE-4", "CBS", "P1", "P2"} <= terms
