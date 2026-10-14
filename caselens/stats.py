"""Bulk statistics for chat questions: by type, by sub-type, and longest stage per case.

All figures come from pandas via summary.case_facts. No model call. Average turnaround uses closed
cases only, because open cases have no final turnaround.
"""

import re

import pandas as pd

import summary
from metrics import bottleneck_per_case

AVG_Q = re.compile(r"\b(average|avg|mean)\b", re.IGNORECASE)
PCT_Q = re.compile(r"%|\bpercent\w*|\brates?\b|\bshare\b", re.IGNORECASE)
STAGE_Q = re.compile(r"\b(longest stage|stage counts?|per stage|by stage)\b", re.IGNORECASE)
GROUP_TYPE_Q = re.compile(r"\b(by|per|each)\s+(sub[\s-]?)?types?\b|\bbreakdown\b|\bdistribution\b", re.IGNORECASE)
SUB_Q = re.compile(r"\bsub[\s-]?types?\b", re.IGNORECASE)
TYPE_Q = re.compile(r"\btypes?\b", re.IGNORECASE)
CASE_REF = re.compile(r"\bCS-\d{4}-\d{4}\b|\bcase\s*#?\s*\d{3,4}\b", re.IGNORECASE)


def triggers(question: str) -> bool:
    """True for bulk questions. Questions that name a case are left to the case rules."""
    q = question or ""
    if CASE_REF.search(q):
        return False
    return bool(AVG_Q.search(q) or PCT_Q.search(q) or STAGE_Q.search(q) or GROUP_TYPE_Q.search(q))


def case_table(df, patterns) -> pd.DataFrame:
    """One row per case with the fields the statistics need."""
    rows = []
    for cid in df["Case_ID"]:
        f = summary.case_facts(df, cid, patterns)
        rows.append({
            "Type": f["type"],
            "Sub_type": f["sub_type"],
            "Stalled": bool(f["stalls"]),
            "Closed": bool(f["closed"]),
            "TAT": f["tat_hours"],
        })
    return pd.DataFrame(rows)


def metrics_row(g: pd.DataFrame) -> dict:
    closed = g[g["Closed"] & g["TAT"].notna()]
    return {
        "Cases": len(g),
        "Stalled": int(g["Stalled"].sum()),
        "Stalled_pct": round(g["Stalled"].mean() * 100, 1),
        "Avg_TAT_hours": round(closed["TAT"].mean(), 1) if len(closed) else None,
    }


def group_table(t: pd.DataFrame, col: str) -> pd.DataFrame:
    rows = [{col: label, **metrics_row(g)} for label, g in t.groupby(col)]
    return pd.DataFrame(rows)


def _label(value) -> str:
    return str(value).replace("_", " ")


def _line(label, m) -> str:
    avg = "n/a" if pd.isna(m["Avg_TAT_hours"]) else f"{m['Avg_TAT_hours']:.1f} h"
    return (f"- {label} | {m['Cases']} cases | {m['Stalled']} stalled ({m['Stalled_pct']:.1f}%) "
            f"| avg turnaround {avg}")


def _group_text(t, col, heading) -> str:
    lines = [f"{heading} (average turnaround uses closed cases):"]
    for _, row in group_table(t, col).iterrows():
        lines.append(_line(_label(row[col]), row))
    return "\n".join(lines)


def stage_text(df) -> str:
    bn = bottleneck_per_case(df)
    counts = bn.groupby("Stage").size()
    lines = [f"Longest stage per case ({len(bn)} cases with at least one timed stage):"]
    for n, count in counts.items():
        lines.append(f"- Stage {int(n)} ({summary.STAGE_NAMES[int(n)]}) | {int(count)} cases")
    if len(bn) < len(df):
        lines.append(f"{len(df) - len(bn)} cases have no timed stage yet, so they are not counted.")
    return "\n".join(lines)


def answer(question: str, df, patterns) -> str:
    """Text answer for a bulk question. Uses only figures computed from the case data."""
    q = question or ""
    if STAGE_Q.search(q):
        return stage_text(df)
    t = case_table(df, patterns)
    if SUB_Q.search(q):
        return _group_text(t, "Sub_type", "Stalled cases and turnaround by sub-type")
    if TYPE_Q.search(q):
        return _group_text(t, "Type", "Stalled cases and turnaround by type")
    return "All cases:\n" + _line("All cases", metrics_row(t))
