import re

import pytest

import summary
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


@pytest.fixture(scope="module")
def df():
    return load_cases(CASES_CSV)


@pytest.fixture(scope="module")
def patterns():
    return build_patterns(load_entries(JARGON_JSON))


@pytest.fixture
def no_key(monkeypatch):
    # Force the template path so tests never call the network.
    monkeypatch.setattr(summary, "get_settings", lambda: ("", "test-model"))


def test_mask_removes_client_email_account_and_phone():
    text = "Client CL-90812 mail jane.doe@example.com acct 1234567890 call +1 555 123 4567"
    masked = summary.mask(text)
    assert "CL-90812" not in masked
    assert "jane.doe@example.com" not in masked
    assert "1234567890" not in masked
    assert "555 123 4567" not in masked


def test_mask_keeps_business_numbers():
    assert summary.mask("LTV exceeds 80%. DTI 42%. DSCR is 1.35x.") == "LTV exceeds 80%. DTI 42%. DSCR is 1.35x."


def test_keep_cited_drops_uncited_and_unknown_citations():
    allowed = {"C1", "JD-004"}
    text = "\n".join([
        "- KYC was refreshed [C1] [JD-004]",
        "No citation here",
        "Made-up source [C9]",
    ])
    kept, dropped = summary.keep_cited(text, allowed)
    assert kept == ["KYC was refreshed [C1] [JD-004]"]
    assert dropped == 2


def test_case_facts_finds_bottleneck_for_case_1001(df, patterns):
    facts = summary.case_facts(df, "CS-2026-1001", patterns)
    # CS-2026-1001 has Stage 3 as the longest stage (64.0 h) in the regenerated data
    assert facts["bottleneck"][0] == 3
    assert facts["tat_hours"] == pytest.approx(88.59)


def test_template_summary_lines_all_carry_valid_citations(df, patterns, no_key):
    result = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    assert result["mode"] == "template"
    facts = summary.case_facts(df, "CS-2026-1001", patterns)
    allowed = summary.allowed_sources(facts)
    for line in result["lines"]:
        cites = re.findall(r"\[((?:M\d|C\d|JD-\d{3}))\]", line)
        assert cites, line
        assert set(cites) <= allowed, line


def test_template_output_has_no_raw_client_id(df, patterns, no_key):
    result = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    assert all("CL-90812" not in line for line in result["lines"])


def test_missing_key_falls_back_with_reason(df, patterns, no_key):
    result = summary.summarize_case("CS-2026-1002", df=df, patterns=patterns)
    assert result["mode"] == "template"
    assert result["error"] == "no API key in .env"


def test_unknown_case_raises(df, patterns):
    with pytest.raises(ValueError):
        summary.case_facts(df, "CS-0000-0000", patterns)


def test_closed_detection_on_real_cases(df, patterns):
    assert summary.case_facts(df, "CS-2026-1001", patterns)["closed"] is True
    assert summary.case_facts(df, "CS-2026-1005", patterns)["closed"] is False
    assert summary.case_facts(df, "CS-2026-1008", patterns)["closed"] is False


def test_stall_stages_for_known_cases(df, patterns):
    assert summary.case_facts(df, "CS-2026-1005", patterns)["stalls"] == [3]
    assert summary.case_facts(df, "CS-2026-1002", patterns)["stalls"] == [2]
    assert summary.case_facts(df, "CS-2026-1001", patterns)["stalls"] == []


def test_decision_wording_is_not_a_stall(df, patterns):
    # CS-2026-1001 Stage 3 comment is a decision, not a hold-up.
    assert summary.case_facts(df, "CS-2026-1001", patterns)["stalls"] == []


def test_clean_case_has_no_stall(df, patterns):
    assert summary.case_facts(df, "CS-2026-1001", patterns)["stalls"] == []


def test_prompt_records_past_stall_and_status(df, patterns):
    facts = summary.case_facts(df, "CS-2026-1008", patterns)
    prompt = summary.build_prompt(facts)
    assert "[M3] Stall recorded in Stage 2" in prompt
    assert "[M4] Case status: open" in prompt


def test_template_mentions_stall_with_citation(df, patterns, no_key):
    result = summary.summarize_case("CS-2026-1008", df=df, patterns=patterns)
    stall_lines = [line for line in result["lines"] if "[M3]" in line]
    assert stall_lines
    assert "Stage 2" in stall_lines[0]


def test_card_has_required_sections_and_no_inline_citations(df, patterns, no_key):
    facts = summary.case_facts(df, "CS-2026-1001", patterns)
    result = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    card = summary.render_card(facts, result["lines"])
    for heading in ["Case: CS-2026-1001", "Purpose:", "Created:", "Current Stage:",
                    "Summary:", "Key Events:", "Documents:", "SLA:"]:
        assert heading in card, heading
    assert "04-Dec-2025" in card
    assert "2-day target" in card  # CS-2026-1001 SLA_Days = 2
    assert "✓ Income Proof" in card  # CS-2026-1001 Document_Details
    assert "[C" not in card and "[M" not in card


def test_scheduled_stage5_is_not_closed():
    assert summary.is_closed("CBS updated. Closing scheduled.") is False
    assert summary.is_closed("Closed. Notification sent.") is True


def test_open_language_is_removed_for_closed_cases():
    lines = [
        "Stage 3 is currently stalled [C3]",
        "The case was approved and disbursed [C4]",
        "Next action is to obtain tax returns [C3]",
    ]
    assert summary.drop_open_language(lines) == ["The case was approved and disbursed [C4]"]


def test_current_state_rule_is_always_in_system_prompt(monkeypatch, df, patterns):
    seen = {}

    def fake_call(prompt, key, model, system=summary.SYSTEM_PROMPT, timeout=30):
        seen["system"] = system
        return "Case was resolved [C5]"

    monkeypatch.setattr(summary, "get_settings", lambda: ("fake-key", "test-model"))
    monkeypatch.setattr(summary, "call_llm", fake_call)

    summary.summarize_case("CS-2026-1006", df=df, patterns=patterns)
    assert summary.CURRENT_STATE_RULE in seen["system"]


def test_closed_rule_is_added_to_system_prompt_only_when_closed(monkeypatch, df, patterns):
    seen = {}

    def fake_call(prompt, key, model, system=summary.SYSTEM_PROMPT, timeout=30):
        seen["system"] = system
        return "Case was closed [C5]"

    monkeypatch.setattr(summary, "get_settings", lambda: ("fake-key", "test-model"))
    monkeypatch.setattr(summary, "call_llm", fake_call)

    summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    assert summary.CLOSED_RULE in seen["system"]

    summary.summarize_case("CS-2026-1005", df=df, patterns=patterns)
    assert summary.CLOSED_RULE not in seen["system"]
