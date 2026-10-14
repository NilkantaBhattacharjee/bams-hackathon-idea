"""Data validation for the case CSV. Source files are read only; issues go to a report."""

import json
import re
from pathlib import Path

import pandas as pd

from config import CASES_CSV, JARGON_JSON, REPORT_PATH, TAT_TOLERANCE_HOURS
from metrics import STAGES, load_cases, recalculated_tat_hours, stage_durations

# Heuristic for jargon in comments: all-caps words, letter+digit codes, digit+letter codes,
# and hyphenated codes such as DE-4. Lowercase business phrases are not detected.
TOKEN = re.compile(r"\b(?:[A-Z]+-[0-9]+|[A-Z]{2,}[0-9]*|[A-Z][0-9]+|[0-9]+[A-Z]+)\b")
IGNORED_TOKENS = {"OK"}


def find_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per problem: Case_ID, Check, Detail."""
    issues = []

    for n in range(1, STAGES + 1):
        col = f"Stage_{n}_Timestamp"
        for cid in df.loc[df[col].isna(), "Case_ID"]:
            issues.append((cid, "missing_or_invalid_timestamp", f"Stage {n} timestamp is missing or unparseable"))

    durations = stage_durations(df)
    for _, row in durations[durations["Hours"] < 0].iterrows():
        issues.append((
            row["Case_ID"],
            "out_of_order",
            f"Stage {row['Stage'] + 1} starts before Stage {row['Stage']} ({row['Hours']:.1f} h)",
        ))

    computed = recalculated_tat_hours(df)
    stored = df["Total_TAT_Hours"]
    mismatch = (computed - stored).abs() > TAT_TOLERANCE_HOURS
    for i in df.index[mismatch]:
        issues.append((
            df.at[i, "Case_ID"],
            "tat_mismatch",
            f"Stored Total_TAT_Hours {stored[i]} vs recalculated {computed[i]:.2f}",
        ))

    return pd.DataFrame(issues, columns=["Case_ID", "Check", "Detail"])


VALID_PRIORITIES = {"P1", "P2"}


def find_governance_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Checks on the added client, priority and status fields. Returns Case_ID, Check, Detail."""
    issues = []

    if "Client_Email" in df.columns:
        emails = df["Client_Email"].astype(str).str.strip().str.lower()
        dupes = df.loc[emails.duplicated(keep=False) & (emails != ""), "Case_ID"]
        for cid in dupes:
            issues.append((cid, "duplicate_email", "Client_Email is shared with another case"))

    if "Priority" in df.columns:
        for cid in df.loc[~df["Priority"].isin(VALID_PRIORITIES), "Case_ID"]:
            issues.append((cid, "missing_priority", "Priority is not P1 or P2"))

    if "Case_Status" in df.columns:
        has_stage5 = df["Stage_5_Timestamp"].notna()
        is_open = df["Case_Status"].str.strip().str.lower() == "open"
        for cid in df.loc[is_open & has_stage5, "Case_ID"]:
            issues.append((cid, "open_with_stage5", "Case is Open but has a Stage 5 timestamp"))
        for cid in df.loc[~is_open & ~has_stage5, "Case_ID"]:
            issues.append((cid, "closed_without_stage5", "Case is Closed but has no Stage 5 timestamp"))

    return pd.DataFrame(issues, columns=["Case_ID", "Check", "Detail"])


def load_terms(path=JARGON_JSON) -> set[str]:
    """Upper-cased dictionary terms."""
    entries = json.loads(Path(path).read_text(encoding="utf-8"))
    return {entry["Term"].upper() for entry in entries}


def extract_tokens(text: str) -> set[str]:
    return {tok for tok in TOKEN.findall(text) if tok not in IGNORED_TOKENS}


def term_coverage(df: pd.DataFrame, terms: set[str]) -> pd.DataFrame:
    """Jargon-like tokens in comments that are not in the dictionary, with the cases they appear in."""
    found: dict[str, set[str]] = {}
    comment_cols = [c for c in df.columns if c.endswith("_Comments")]
    for col in comment_cols:
        for cid, text in zip(df["Case_ID"], df[col].fillna("")):
            for tok in extract_tokens(text):
                if tok.upper() not in terms:
                    found.setdefault(tok, set()).add(cid)
    rows = [
        {"Token": tok, "Case_count": len(cases), "Case_IDs": ", ".join(sorted(cases))}
        for tok, cases in sorted(found.items())
    ]
    return pd.DataFrame(rows, columns=["Token", "Case_count", "Case_IDs"])


def write_report(df: pd.DataFrame, issues: pd.DataFrame, unmatched: pd.DataFrame, path=REPORT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Data Validation Report",
        "",
        f"- Cases checked: {len(df)}",
        f"- Issues found: {len(issues)}",
        f"- Jargon-like tokens not in dictionary: {len(unmatched)}",
        "",
        "## Issues",
        "",
    ]
    if issues.empty:
        lines.append("No issues found.")
    else:
        lines.append(issues.to_markdown(index=False))
    lines += ["", "## Tokens not in dictionary", ""]
    if unmatched.empty:
        lines.append("All detected tokens are in the dictionary.")
    else:
        lines.append(unmatched.to_markdown(index=False))
    lines += [
        "",
        "Note: the token check only finds all-caps and code-style terms. Lowercase phrases "
        "(for example, 'gift letter') are not checked.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_cases(CASES_CSV)
    issues = pd.concat([find_issues(df), find_governance_issues(df)], ignore_index=True)
    unmatched = term_coverage(df, load_terms(JARGON_JSON))
    write_report(df, issues, unmatched)
    print(f"Cases: {len(df)}  Issues: {len(issues)}  Unmatched tokens: {len(unmatched)}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
