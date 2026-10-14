"""Dictionary lookup for jargon in case comments.

Each dictionary Term and Full_Form is matched as a whole phrase, ignoring case.
Matches return the dictionary ID so every explanation can be cited. Text that is
not in the dictionary is reported, never guessed.
"""

import json
import re
from pathlib import Path

import pandas as pd

from config import CASES_CSV, JARGON_JSON, JARGON_REPORT_PATH
from metrics import STAGES, load_cases

COMMENT_COLS = [f"Stage_{n}_Comments" for n in range(1, STAGES + 1)]


def load_entries(path=JARGON_JSON) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_patterns(entries: list[dict]) -> list[tuple[re.Pattern, dict, int]]:
    """One regex per Term and Full_Form. Longer phrases come first so they win overlaps."""
    patterns = []
    for entry in entries:
        for alias in {entry["Term"], entry.get("Full_Form", "")}:
            if not alias:
                continue
            regex = re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", re.IGNORECASE)
            patterns.append((regex, entry, len(alias)))
    patterns.sort(key=lambda p: -p[2])
    return patterns


def find_terms(text, patterns) -> list[dict]:
    """Dictionary hits in a comment, in the order they appear. Each term is reported once."""
    if not isinstance(text, str) or not text.strip():
        return []
    taken: list[tuple[int, int]] = []
    hits: dict[str, tuple[int, dict]] = {}
    for regex, entry, _ in patterns:
        for m in regex.finditer(text):
            if any(m.start() < end and start < m.end() for start, end in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.setdefault(entry["ID"], (m.start(), {
                "ID": entry["ID"],
                "Term": entry["Term"],
                "Full_Form": entry.get("Full_Form", ""),
                "Matched_Text": m.group(0),
                "Plain_English_Explanation": entry["Plain_English_Explanation"],
                "Status": entry.get("Status", ""),
            }))
    return [record for _, record in sorted(hits.values(), key=lambda h: h[0])]


def explain_comments(df: pd.DataFrame, patterns) -> pd.DataFrame:
    """One row per matched term per stage comment."""
    rows = []
    for _, case in df.iterrows():
        for n, col in enumerate(COMMENT_COLS, start=1):
            comment = case[col]
            for hit in find_terms(comment, patterns):
                rows.append({
                    "Case_ID": case["Case_ID"],
                    "Stage": n,
                    "Comment": comment,
                    **hit,
                })
    return pd.DataFrame(rows)


def comments_without_match(df: pd.DataFrame, patterns) -> pd.DataFrame:
    """Non-empty stage comments where no dictionary term was found."""
    rows = []
    for _, case in df.iterrows():
        for n, col in enumerate(COMMENT_COLS, start=1):
            comment = case[col]
            if isinstance(comment, str) and comment.strip() and not find_terms(comment, patterns):
                rows.append({"Case_ID": case["Case_ID"], "Stage": n, "Comment": comment})
    return pd.DataFrame(rows)


def write_report(df, matches, unmatched, path=JARGON_REPORT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    total_comments = sum(df[c].notna().sum() for c in COMMENT_COLS)
    matched_comments = matches[["Case_ID", "Stage"]].drop_duplicates().shape[0] if not matches.empty else 0
    per_term = (
        matches.groupby(["ID", "Term"]).size().reset_index(name="Comment_hits").sort_values("Comment_hits", ascending=False)
        if not matches.empty else pd.DataFrame(columns=["ID", "Term", "Comment_hits"])
    )
    lines = [
        "# Jargon Lookup Report",
        "",
        f"- Cases: {len(df)}",
        f"- Stage comments: {total_comments}",
        f"- Stage comments with at least one dictionary term: {matched_comments}",
        f"- Stage comments with no dictionary term: {len(unmatched)}",
        "",
        "## Dictionary terms found in comments",
        "",
        per_term.to_markdown(index=False) if not per_term.empty else "No terms found.",
        "",
        "## Comments with no dictionary term",
        "",
        "These need review. Either the dictionary is missing a term, or the comment has no jargon.",
        "",
        unmatched.to_markdown(index=False) if not unmatched.empty else "All comments matched.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = load_cases(CASES_CSV)
    patterns = build_patterns(load_entries(JARGON_JSON))
    matches = explain_comments(df, patterns)
    unmatched = comments_without_match(df, patterns)
    write_report(df, matches, unmatched)
    print(f"Comments with a term: {matches[['Case_ID', 'Stage']].drop_duplicates().shape[0]}  "
          f"Without a term: {len(unmatched)}")
    print(f"Report: {JARGON_REPORT_PATH}")


if __name__ == "__main__":
    main()
