import chat
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _data():
    entries = load_entries(JARGON_JSON)
    return load_cases(CASES_CSV), entries, build_patterns(entries)


def _ask(question):
    df, entries, patterns = _data()
    return chat.answer(question, df, patterns, entries, history=[])["text"]


def test_closed_case_needs_no_client_action():
    text = _ask("What is needed from the client to proceed with CS-2026-1101?")
    assert "No action is needed from the client" in text


def test_open_case_client_needs_show_stage():
    text = _ask("What is needed from the client to proceed with CS-2026-1103?")
    assert "open at Stage" in text


def test_additional_document_question_is_answered():
    text = _ask("Is there any additional document required for CS-2026-1103?")
    assert text.startswith(("Additional documents still pending", "No additional documents"))


def test_long_closure_question_gives_turnaround_reason():
    text = _ask("Why did CS-2026-1005 take a long time to get closed?")
    assert "Total turnaround" in text


def test_case_answers_have_no_contact_details():
    df, _, _ = _data()
    row = df[df["Case_ID"] == "CS-2026-1103"].iloc[0]
    for q in ["What is needed from the client to proceed with CS-2026-1103?",
              "Why did CS-2026-1103 take a long time?"]:
        text = _ask(q)
        for value in [row["Client_Email"], row["Account_Number"], row["Contact_Phone"], row["Client_Name"]]:
            assert str(value) not in text
