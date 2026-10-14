"""One-time: add an explicit Case_Status column (Open or Closed) to the case CSV.

Rule used to set the value:
- Open: the Stage 5 comment is blank (case has not reached a final outcome) or says "scheduled".
- Closed: every other case.

The backup is written first. Does nothing if Case_Status already exists.
"""

import re
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, for config
from config import CASES_CSV  # noqa: E402

SCHEDULED = re.compile(r"\bscheduled\b", re.IGNORECASE)


def status_for(stage5_comment) -> str:
    text = stage5_comment.strip() if isinstance(stage5_comment, str) else ""
    if not text or SCHEDULED.search(text):
        return "Open"
    return "Closed"


def main() -> None:
    df = pd.read_csv(CASES_CSV, dtype=str, keep_default_na=False)
    if "Case_Status" in df.columns:
        print("Case_Status already present; nothing changed.")
        return

    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before case status).csv")
    shutil.copyfile(CASES_CSV, backup)

    df["Case_Status"] = [status_for(c) for c in df["Stage_5_Comments"]]
    df.to_csv(CASES_CSV, index=False)
    counts = df["Case_Status"].value_counts().to_dict()
    print(f"Added Case_Status: {counts}. Backup: {backup.name}")


if __name__ == "__main__":
    main()
