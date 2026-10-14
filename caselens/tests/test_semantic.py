import pytest

import semantic
from config import JARGON_JSON
from jargon import load_entries

needs_model = pytest.mark.skipif(not semantic.available(), reason="sentence-transformers model not available")


@pytest.fixture(scope="module")
def entries():
    return load_entries(JARGON_JSON)


def test_unavailable_model_returns_no_matches(monkeypatch, entries):
    monkeypatch.setattr(semantic, "available", lambda: False)
    assert semantic.search_glossary("home loan refinancing", entries) == []


def test_empty_query_returns_no_matches(entries):
    assert semantic.search_glossary("   ", entries) == []


@needs_model
def test_meaning_match_finds_mortgage_refinance(entries):
    hits = semantic.search_glossary("refinancing my home loan to a lower rate", entries)
    assert any(h["ID"] == "JD-052" for h in hits)


@needs_model
def test_unrelated_query_returns_nothing(entries):
    assert semantic.search_glossary("what is the weather in Paris today", entries) == []


@needs_model
def test_matches_are_ranked_best_first(entries):
    hits = semantic.search_glossary("loan to value ratio of the property", entries)
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)
