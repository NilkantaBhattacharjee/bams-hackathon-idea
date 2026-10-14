import pytest

import summary
import trends
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import load_cases


@pytest.fixture(scope="module")
def df():
    return load_cases(CASES_CSV)


@pytest.fixture(scope="module")
def patterns():
    return build_patterns(load_entries(JARGON_JSON))


@pytest.fixture(scope="module")
def figs(df, patterns):
    return trends.compute_figures(df, patterns)


def test_total_case_count_matches_data(df, figs):
    assert figs["T1"].startswith(f"{len(df)} cases analysed")


def test_stalled_count_matches_case_facts(df, patterns, figs):
    stalled = sum(bool(summary.case_facts(df, c, patterns)["stalls"]) for c in df["Case_ID"])
    assert f"{stalled} with a recorded stall" in figs["T1"]


def test_average_turnaround_matches_stored_tat(df, figs):
    assert f"{df['Total_TAT_Hours'].astype(float).mean():.1f} hours" in figs["T2"]


def test_every_figure_has_an_id(figs):
    assert all(k.startswith("T") for k in figs)
    assert len(figs) >= 5


def test_template_narrative_cites_only_known_ids(figs, monkeypatch):
    monkeypatch.setattr(trends, "get_settings", lambda: ("", "m"))
    lines, mode = trends.narrative(figs)
    assert mode == "template"
    for line in lines:
        cites = summary.CITATION.findall(line)
        assert cites and set(cites) <= set(figs)


def test_uncited_model_output_falls_back(figs, monkeypatch):
    monkeypatch.setattr(trends, "get_settings", lambda: ("fake", "m"))
    monkeypatch.setattr(trends, "call_llm_with_retry", lambda *a, **k: "Trends look bad with no source.")
    lines, mode = trends.narrative(figs)
    assert mode == "template"


def test_cited_model_output_is_kept(figs, monkeypatch):
    monkeypatch.setattr(trends, "get_settings", lambda: ("fake", "m"))
    monkeypatch.setattr(trends, "call_llm_with_retry", lambda *a, **k: "Most cases are summarised here [T1].")
    lines, mode = trends.narrative(figs)
    assert mode == "llm"
    assert lines == ["Most cases are summarised here [T1]."]


def test_unknown_figure_id_is_dropped(figs, monkeypatch):
    monkeypatch.setattr(trends, "get_settings", lambda: ("fake", "m"))
    monkeypatch.setattr(trends, "call_llm_with_retry", lambda *a, **k: "Made up claim [T99].")
    lines, mode = trends.narrative(figs)
    assert mode == "template"
