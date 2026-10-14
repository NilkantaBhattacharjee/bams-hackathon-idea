"""One-time: add client contact and priority fields to the case CSV.

All values are SYNTHETIC. Names are fictional, phone numbers use the 555 test range, emails use
the example.com domain, and account numbers are random. Values are seeded so reruns match.
The script backs up the original file first and does nothing if the fields already exist.
"""

import re
import random
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, for config
from config import CASES_CSV  # noqa: E402

FIRST_NAMES = ["Aarav", "Meera", "Daniel", "Sofia", "Kenji", "Amara", "Lucas", "Priya", "Omar", "Elena",
               "Ravi", "Hannah", "Mateo", "Leila", "Samuel", "Nadia", "Ethan", "Ingrid", "Tariq", "Chloe"]
LAST_NAMES = ["Sharma", "Patel", "Walker", "Rossi", "Tanaka", "Okafor", "Silva", "Iyer", "Haddad", "Novak",
              "Brown", "Kim", "Garcia", "Ahmed", "Lindqvist", "Mehta", "Clarke", "Moreau", "Rao", "Adams"]

NEW_COLS = ["Client_Name", "Account_Number", "Client_Email", "Contact_Phone", "Priority"]
PRIORITY = re.compile(r"\bP([12])\b")


def priority_from_comments(row) -> str:
    """Use the priority written in the stage comments (P1 or P2). Default P2 when none is recorded."""
    for n in range(1, 6):
        m = PRIORITY.search(str(row[f"Stage_{n}_Comments"]))
        if m:
            return f"P{m.group(1)}"
    return "P2"


def main() -> None:
    df = pd.read_csv(CASES_CSV, dtype=str, keep_default_na=False)
    if all(col in df.columns for col in NEW_COLS):
        print("Fields already present; nothing changed.")
        return

    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before contact fields).csv")
    shutil.copyfile(CASES_CSV, backup)

    rng = random.Random(2026)
    names, accounts, emails, phones, priorities = [], [], [], [], []
    for _, row in df.iterrows():
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        names.append(f"{first} {last}")
        accounts.append(str(rng.randint(10**9, 10**10 - 1)))
        emails.append(f"{first.lower()}.{last.lower()}{rng.randint(10, 99)}@example.com")
        phones.append(f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}")
        priorities.append(priority_from_comments(row))

    df["Client_Name"] = names
    df["Account_Number"] = accounts
    df["Client_Email"] = emails
    df["Contact_Phone"] = phones
    df["Priority"] = priorities
    df.to_csv(CASES_CSV, index=False)
    print(f"Added {', '.join(NEW_COLS)} to {len(df)} rows. Backup: {backup.name}")


if __name__ == "__main__":
    main()
