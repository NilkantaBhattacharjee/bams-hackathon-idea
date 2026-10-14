import chat
import guardrails
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _data():
    entries = load_entries(JARGON_JSON)
    return load_cases(CASES_CSV), entries, build_patterns(entries)


def test_questions_asking_for_personal_details_are_refused():
    df, entries, patterns = _data()
    questions = [
        "What is the email of CS-2026-1101?",
        "Give me the phone number for CS-2026-1101",
        "What is the account number of CS-2026-1101?",
        "Who is the client for CS-2026-1101?",
        "What is the client name for CS-2026-1101?",
    ]
    for q in questions:
        assert chat.answer(q, df, patterns, entries, history=[])["text"] == chat.PII_NOTE, q


def test_redact_output_masks_contact_details():
    text = "Mail jane.doe42@example.com or +1-555-123-4567, account 1234567890, client CL-90812"
    out = guardrails.redact_output(text)
    assert "@" not in out
    assert "555-123" not in out
    assert "1234567890" not in out
    assert "CL-90812" not in out


def test_case_answers_contain_no_contact_details():
    df, entries, patterns = _data()
    reply = chat.answer("Is CS-2026-1101 closed?", df, patterns, entries, history=[])
    row = df[df["Case_ID"] == "CS-2026-1101"].iloc[0]
    for value in [row["Client_Email"], row["Account_Number"], row["Contact_Phone"], row["Client_Name"]]:
        assert str(value) not in reply["text"]
