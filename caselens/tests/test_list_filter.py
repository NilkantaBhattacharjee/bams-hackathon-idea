import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _data():
    entries = load_entries(JARGON_JSON)
    return load_cases(CASES_CSV), entries, build_patterns(entries)


def test_list_by_sub_type_returns_only_that_sub_type():
    df, entries, patterns = _data()
    text = chat.answer("Can you list out all the personal loan type of cases?", df, patterns, entries,
                       history=[])["text"]
    rows = [line for line in text.splitlines() if line.startswith("- CS-")]
    assert rows, text
    assert all("Personal Loan" in line for line in rows)


def test_count_matches_data_for_sub_type():
    df, entries, patterns = _data()
    expected = int((df["Specific_Sub_Type"] == "Personal_Loan").sum())
    text = chat.answer("how many personal loan cases are there?", df, patterns, entries, history=[])["text"]
    assert text.startswith(f"{expected} case(s) Personal Loan:"), text


def test_verification_confirms_all_listed_are_personal_loan():
    df, entries, patterns = _data()
    listed = chat.answer("Can you list out all the personal loan type of cases?", df, patterns, entries,
                         history=[])
    history = [{"role": "user", "content": "list personal loan cases"},
               {"role": "assistant", "content": listed["text"]}]
    text = chat.answer("Are all of these cases are personal loan type of cases?", df, patterns, entries,
                       history=history)["text"]
    assert text.startswith("Yes."), text


def test_verification_flags_a_case_that_is_not_personal_loan():
    df, entries, patterns = _data()
    other = df.loc[df["Specific_Sub_Type"] != "Personal_Loan", "Case_ID"].iloc[0]
    history = [{"role": "assistant", "content": f"- {other} | Retail Banking / Mortgage Refinance"}]
    text = chat.answer("Are all of these cases personal loan type?", df, patterns, entries, history=history)["text"]
    assert text.startswith("No."), text
    assert other in text
