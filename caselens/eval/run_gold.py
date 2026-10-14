"""Gold question check for the chat. Offline: the model is disabled, so only rule and figure answers run.

Checks per question:
- must_contain: text that must appear. {placeholders} are filled from figures computed from the CSV.
- must_not_contain: text that must not appear.
- case_ids: the case IDs the reply should list, when given.
- privacy: no client email, phone, account number or client name from the CSV may appear in any answer.

Run from anywhere: py eval\run_gold.py   (writes eval\gold_results.md; exit code 1 on any failure)
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import chat  # noqa: E402
import stats  # noqa: E402
import summary  # noqa: E402
from config import CASES_CSV, JARGON_JSON  # noqa: E402
from jargon import build_patterns, load_entries  # noqa: E402
from metrics import bottleneck_per_case, load_cases  # noqa: E402

GOLD = Path(__file__).with_name("gold_questions.json")
REPORT = Path(__file__).with_name("gold_results.md")
PII_COLUMNS = ["Client_Email", "Account_Number", "Contact_Phone", "Client_Name"]


def expected_values(df, patterns) -> dict:
    """Figures computed from the CSV, independent of the chat's answer code."""
    t = stats.case_table(df, patterns)
    return {
        "stalled": int(t["Stalled"].sum()),
        "closed": int(t["Closed"].sum()),
        "open": int((~t["Closed"]).sum()),
        "total": len(t),
    }


def valid_counts(df, patterns) -> set[int]:
    """Counts that may appear in an answer. Every one is derived from the CSV."""
    t = stats.case_table(df, patterns)
    valid = {len(t), int(t["Stalled"].sum()), int(t["Closed"].sum()), int((~t["Closed"]).sum())}
    for col in ["Type", "Sub_type"]:
        g = stats.group_table(t, col)
        valid |= {int(x) for x in g["Cases"]} | {int(x) for x in g["Stalled"]}
    bn = bottleneck_per_case(df)
    valid |= {int(x) for x in bn.groupby("Stage").size()} | {len(bn), len(df) - len(bn)}
    return valid


def run(questions=None) -> list[dict]:
    specs = questions if questions is not None else json.loads(GOLD.read_text(encoding="utf-8"))
    df = load_cases(CASES_CSV)
    entries = load_entries(JARGON_JSON)
    patterns = build_patterns(entries)
    values = expected_values(df, patterns)
    valid = valid_counts(df, patterns)
    pii = {str(v) for col in PII_COLUMNS for v in df[col].tolist() if str(v).strip()}

    original = summary.get_settings
    summary.get_settings = lambda: ("", summary.DEFAULT_MODEL)  # offline: no model call
    try:
        results = []
        for spec in specs:
            reply = chat.answer(spec["question"], df, patterns, entries, history=[])
            text = reply["text"]
            failures = []
            for needle in spec.get("must_contain", []):
                expected = needle.format(**values)
                if expected not in text:
                    failures.append(f"missing: {expected}")
            if "any_of" in spec and not any(n in text for n in spec["any_of"]):
                failures.append(f"none of: {spec['any_of']}")
            for needle in spec.get("must_not_contain", []):
                if needle in text:
                    failures.append(f"forbidden: {needle}")
            if "case_ids" in spec and reply.get("case_ids") != spec["case_ids"]:
                failures.append(f"case_ids {reply.get('case_ids')} != {spec['case_ids']}")
            unknown = [n for n in (int(x) for x in re.findall(r"(\d+) case", text)) if n not in valid]
            if unknown:
                failures.append(f"figure not in data: {unknown}")
            if any(value in text for value in pii):
                failures.append("privacy: contact detail in answer")
            results.append({"id": spec["id"], "question": spec["question"],
                            "passed": not failures, "failures": failures})
    finally:
        summary.get_settings = original
    return results


def main() -> int:
    results = run()
    passed = sum(r["passed"] for r in results)
    lines = [
        "# Gold Question Results",
        "",
        f"- Date: {date.today().isoformat()}",
        f"- Passed: {passed} of {len(results)}",
        "- Mode: offline (rules and computed figures, no model call)",
        "",
        "| ID | Question | Result | Failures |",
        "|---|---|---|---|",
    ]
    for r in results:
        result = "PASS" if r["passed"] else "FAIL"
        lines.append(f"| {r['id']} | {r['question']} | {result} | {'; '.join(r['failures'])} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Gold questions passed: {passed}/{len(results)}. Report: {REPORT}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
