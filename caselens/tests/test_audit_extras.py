import pandas as pd

import audit_view as av


def _log():
    return pd.DataFrame([
        {"ts": pd.Timestamp("2026-10-01", tz="UTC"), "kind": "summary", "model": "m", "prompt_version": "v1",
         "case_ids": ["CS-2026-1001"], "citations": [], "dropped_lines": 2, "error": "",
         "latency_ms": 1000.0, "total_tokens": 1000},
        {"ts": pd.Timestamp("2026-10-02", tz="UTC"), "kind": "chat", "model": "m", "prompt_version": "v2",
         "case_ids": ["CS-2026-1001", "CS-2026-1002"], "citations": [], "dropped_lines": 0, "error": "",
         "latency_ms": 2000.0, "total_tokens": 2000},
        {"ts": pd.Timestamp("2026-10-03", tz="UTC"), "kind": "feedback", "model": "", "prompt_version": "v2",
         "case_ids": [], "citations": [], "dropped_lines": 0, "error": "up",
         "latency_ms": None, "total_tokens": None},
        {"ts": pd.Timestamp("2026-10-04", tz="UTC"), "kind": "feedback", "model": "", "prompt_version": "v2",
         "case_ids": [], "citations": [], "dropped_lines": 0, "error": "down",
         "latency_ms": None, "total_tokens": None},
    ])


def test_prompt_version_table_compares_versions():
    out = av.by_prompt_version(_log()).set_index("prompt_version")
    assert out.loc["v1", "dropped_lines"] == 2
    assert out.loc["v2", "model_calls"] == 1
    assert out.loc["v2", "avg_latency_ms"] == 2000


def test_cost_by_case_splits_tokens_across_named_cases():
    out = av.cost_by_case(_log(), price_per_1k=0.001).set_index("case_id")
    # CS-2026-1001 is named in two calls: 1000 + 2000 tokens at $0.001 per 1K = $0.003
    assert round(out.loc["CS-2026-1001", "est_cost_usd"], 5) == 0.003
    assert out.loc["CS-2026-1002", "calls"] == 1


def test_cost_by_case_is_empty_without_a_price():
    assert av.cost_by_case(_log(), price_per_1k=0).empty


def test_feedback_counts_and_share():
    fb = av.feedback_summary(_log())
    assert fb["up"] == 1 and fb["down"] == 1 and fb["total"] == 2
    assert fb["helpful_share"] == 0.5


def test_feedback_is_empty_when_no_votes():
    fb = av.feedback_summary(_log().iloc[:2])
    assert fb["total"] == 0 and fb["helpful_share"] is None
