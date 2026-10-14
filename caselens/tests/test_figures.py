import chat
import summary
from config import JARGON_JSON
from jargon import load_entries


def test_llm_figure_citations_kept_and_unknown_figures_dropped(monkeypatch):
    entries = load_entries(JARGON_JSON)
    monkeypatch.setattr(summary, "get_settings", lambda: ("test-key", "test-model"))
    monkeypatch.setattr(
        chat,
        "call_chat",
        lambda messages, key, model: "Stalled cases are 27 of 150. [T1]\nInvented figure. [T99]",
    )
    reply = chat.llm_answer("how many are stalled", entries, extra="[T1] 150 cases, 27 stalled.")
    assert reply is not None
    assert "[T1]" in reply["text"]
    assert "T99" not in reply["text"]
