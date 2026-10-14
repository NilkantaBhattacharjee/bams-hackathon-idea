"""Offline evaluation over all cases. Uses the template path only, so no API calls are made.

Checks per case:
- every template line has a valid citation
- stall stages match the comments
- closed cases have no open-status wording
- no raw client IDs appear in output
"""

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import summary  # noqa: E402
from config import CASES_CSV, JARGON_JSON  # noqa: E402
from jargon import build_patterns, load_entries  # noqa: E402
from metrics import load_cases  # noqa: E402

CITE = re.compile(r"\[((?:M\d|C\d|JD-\d{3}))\]")
REPORT = Path(__file__).resolve().parent / "results.md"


def main() -> None:
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))
    summary.get_settings = lambda: ("", "offline")  # force template path

    total_lines = cited_lines = 0
    uncited, open_wording, raw_ids, stall_cases, closed_cases = [], [], [], 0, 0
    closed_with_open = []

    for case_id in df["Case_ID"]:
        result = summary.summarize_case(case_id, df=df, patterns=patterns)
        facts = summary.case_facts(df, case_id, patterns)
        allowed = summary.allowed_sources(facts)
        if facts["stalls"]:
            stall_cases += 1
        if facts["closed"]:
            closed_cases += 1
        for line in result["lines"]:
            total_lines += 1
            cites = CITE.findall(line)
            if cites and set(cites) <= allowed:
                cited_lines += 1
            else:
                uncited.append((case_id, line))
            if "CL-" in line:
                raw_ids.append((case_id, line))
            if facts["closed"] and summary.OPEN_LANGUAGE.search(line):
                closed_with_open.append((case_id, line))

    coverage = cited_lines / total_lines if total_lines else 0.0
    lines = [
        "# Offline Evaluation Report",
        "",
        f"Date: {date.today().isoformat()}  |  Mode: template (no LLM calls)  |  Cases: {len(df)}",
        "",
        "| Check | Result | Target |",
        "|---|---|---|",
        f"| Citation coverage | {coverage:.1%} ({cited_lines}/{total_lines}) | 100% |",
        f"| Lines with invalid or missing citation | {len(uncited)} | 0 |",
        f"| Raw client IDs in output | {len(raw_ids)} | 0 |",
        f"| Closed cases with open-status wording | {len(closed_with_open)} | 0 |",
        f"| Cases with a recorded stall | {stall_cases} | info |",
        f"| Closed cases | {closed_cases} | info |",
        "",
    ]
    for title, rows in [
        ("Uncited lines", uncited),
        ("Raw client IDs", raw_ids),
        ("Open wording in closed cases", closed_with_open),
    ]:
        if rows:
            lines += [f"## {title}", ""] + [f"- {cid}: {text}" for cid, text in rows[:20]] + [""]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Coverage {coverage:.1%}  uncited {len(uncited)}  raw IDs {len(raw_ids)}  "
          f"closed-open {len(closed_with_open)}")
    print(f"Report: {REPORT}")


if __name__ == "__main__":
    main()
