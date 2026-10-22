import summary
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


def _setup(monkeypatch, calls):
    monkeypatch.setattr(summary, "get_settings", lambda: ("fake-key", "test-model"))
    monkeypatch.setattr(summary, "LAST_CALL", {"tokens": 100, "latency_ms": 5})

    def fake_call(prompt, key, model, system, attempts=2):
        calls.append(prompt)
        return "The case was logged and closed [C5]"

    monkeypatch.setattr(summary, "call_llm_with_retry", fake_call)
    monkeypatch.setattr(summary, "SUMMARY_CACHE", {})


def test_second_summary_is_served_from_cache(monkeypatch):
    calls = []
    _setup(monkeypatch, calls)
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))

    first = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    second = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)

    assert len(calls) == 1, "the model should be called once for repeat requests"
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["lines"] == first["lines"]


def test_different_case_is_not_served_from_cache(monkeypatch):
    calls = []
    _setup(monkeypatch, calls)
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))

    summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)
    result = summary.summarize_case("CS-2026-1002", df=df, patterns=patterns)

    assert len(calls) == 2
    assert result["cached"] is False


def test_no_cache_without_a_key(monkeypatch):
    calls = []
    _setup(monkeypatch, calls)
    monkeypatch.setattr(summary, "get_settings", lambda: ("", "test-model"))
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))

    result = summary.summarize_case("CS-2026-1001", df=df, patterns=patterns)

    assert calls == []
    assert result["mode"] == "template"
    assert summary.SUMMARY_CACHE == {}
