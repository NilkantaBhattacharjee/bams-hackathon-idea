"""Evaluation scorecard: each judged target from the handoff, measured against live data.

Grounding and PII checks run the template path over every case (no model calls). Latency, tokens,
and guardrail counts come from the audit log. A target with no measurement is shown as "not measured",
never as a pass.
"""

import re

import pandas as pd

from contextlib import contextmanager

import audit_view
import chat
import summary

CITE = re.compile(r"\[((?:M\d|C\d|JD-\d{3}))\]")
GROUNDING_TARGET = 0.95
LATENCY_TARGET_MS = 5000  # "a single case in a few seconds"
PII_TARGET = 0
HALLUCINATION_TARGET = 1.0  # every invented term must get no definition
JD_CITE = re.compile(r"\[JD-\d{3}\]")

# Made-up terms. None of them is in the dictionary, so any dictionary citation is an invented definition.
INVENTED_TERMS = [
    "Quantum Collateral Index", "Zentrix liquidity ratio", "Orbital settlement factor",
    "Helix margin multiplier", "Varnex capital buffer", "Kestrel exposure score",
    "Lumina drawdown index", "Pyrolex risk coefficient", "Ferrant yield gap",
    "Solenix covenant ratio", "Brightwave clearing quotient", "Nimbora refinance index",
    "Taleris credit halo", "Vorlex accrual tier", "Mirando hedge ratio",
    "Clarivex tranche weight", "Dunmore swap spread", "Oberlin arrears factor",
    "Quorix settlement lag", "Stratafin leverage band", "Ventora pledge score",
    "Halcyon reserve multiple", "Ardent liquidity haircut", "Pellucid default vector",
    "Sigma-Nexus turnover rate", "Caldera loss-given scalar", "Ruvex provision index",
    "Tenebra exposure band", "Zephyrin funding curve", "Morvane capital charge",
]


def grounding(df: pd.DataFrame, patterns) -> dict:
    """Share of template summary lines with a valid citation, over all cases."""
    total = cited = 0
    for case_id in df["Case_ID"]:
        result = summary.summarize_case(case_id, df=df, patterns=patterns, use_llm=False)
        facts = summary.case_facts(df, case_id, patterns)
        allowed = summary.allowed_sources(facts)
        for line in result["lines"]:
            total += 1
            cites = CITE.findall(line)
            if cites and set(cites) <= allowed:
                cited += 1
    share = cited / total if total else None
    return {"value": share, "detail": f"{cited}/{total} lines cited"}


def pii_in_output(df: pd.DataFrame, patterns) -> dict:
    """Raw client IDs in template output. Counts only, never the values."""
    leaks = 0
    for case_id in df["Case_ID"]:
        result = summary.summarize_case(case_id, df=df, patterns=patterns, use_llm=False)
        leaks += sum(1 for line in result["lines"] if "CL-" in line)
    return {"value": leaks, "detail": f"{leaks} raw client IDs in template output"}


def latency_p95(log: pd.DataFrame) -> dict:
    model = audit_view.model_events(log)["latency_ms"].dropna()
    if model.empty:
        return {"value": None, "detail": "no model calls in the audit log"}
    p95 = float(model.quantile(0.95))
    return {"value": p95, "detail": f"p95 over {len(model)} model calls"}


def tokens_per_call(log: pd.DataFrame) -> dict:
    tok = audit_view.model_events(log)["total_tokens"].dropna()
    if tok.empty:
        return {"value": None, "detail": "no token counts in the audit log"}
    return {"value": float(tok.mean()), "detail": f"mean over {len(tok)} model calls"}


@contextmanager
def offline():
    """Run with no API key, then restore the original settings. Keeps the scorecard free of model calls."""
    original = summary.get_settings
    summary.get_settings = lambda: ("", "offline")
    try:
        yield
    finally:
        summary.get_settings = original


def hallucination(df: pd.DataFrame, patterns, entries) -> dict:
    """Share of invented terms that get no dictionary citation. Offline routing check: no model is called."""
    fabricated = refused = 0
    with offline():
        for term in INVENTED_TERMS:
            reply = chat.answer(f"What is {term}?", df, patterns, entries, history=[])["text"]
            if JD_CITE.search(reply):
                fabricated += 1
            if "not in the glossary" in reply.lower():
                refused += 1
    total = len(INVENTED_TERMS)
    return {"value": (total - fabricated) / total,
            "detail": f"{total - fabricated}/{total} invented terms with no definition; "
                      f"{refused} said 'not in the glossary'"}


def build(df: pd.DataFrame, patterns, log: pd.DataFrame, entries) -> pd.DataFrame:
    """One row per target: measured value, target, and pass, fail, or not measured."""
    g = grounding(df, patterns)
    p = pii_in_output(df, patterns)
    h = hallucination(df, patterns, entries)
    lat = latency_p95(log)
    tok = tokens_per_call(log)

    def verdict(value, passed):
        if value is None:
            return "not measured"
        return "pass" if passed else "fail"

    rows = [
        ("Grounding (cited lines)", g["value"] and f"{g['value']:.1%}" or "not measured",
         f"{GROUNDING_TARGET:.0%} or more", g["detail"],
         verdict(g["value"], g["value"] is not None and g["value"] >= GROUNDING_TARGET)),
        ("Raw client IDs in output", str(p["value"]), f"{PII_TARGET}", p["detail"],
         verdict(p["value"], p["value"] == PII_TARGET)),
        ("Invented terms with no definition (offline)", f"{h['value']:.0%}", f"{HALLUCINATION_TARGET:.0%}",
         h["detail"], verdict(h["value"], h["value"] >= HALLUCINATION_TARGET)),
        ("p95 latency (ms)", "not measured" if lat["value"] is None else f"{lat['value']:.0f}",
         f"under {LATENCY_TARGET_MS}", lat["detail"],
         verdict(lat["value"], lat["value"] is not None and lat["value"] < LATENCY_TARGET_MS)),
        ("Tokens per model call", "not measured" if tok["value"] is None else f"{tok['value']:.0f}",
         "tracked (no target)", tok["detail"],
         "not measured" if tok["value"] is None else "info"),
    ]
    return pd.DataFrame(rows, columns=["Target", "Measured", "Target value", "Basis", "Result"])
