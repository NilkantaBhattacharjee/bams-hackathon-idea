"""One-time: append 350 SYNTHETIC cases (CS-2026-1151 to CS-2026-1500) to the case CSV.

Brings the file to 500 cases. Creation dates are spread over the last two years (2024-10-20 to 2026-09-15).
The mix covers open and closed cases, stalled and delayed cases, P1 and P2 priority, document
and no-document cases, and every sub-type. All names, accounts, emails and phone numbers are fictional.
Values are seeded so reruns match. The script backs up the CSV first and does nothing if the new cases exist.
"""

import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, for config
from add_case_fields import SLA_DAYS, document_details  # noqa: E402
from add_contact_fields import FIRST_NAMES, LAST_NAMES, priority_from_comments  # noqa: E402
from add_new_cases import CLOSING, FMT, OPEN_CURRENT, STAGE_POOLS, SUBTYPES  # noqa: E402
from config import CASES_CSV  # noqa: E402

FIRST_NEW_ID = 1151
COUNT = 350
DATE_FROM = datetime(2024, 10, 20)
DATE_TO = datetime(2026, 9, 15)  # keeps every stage timestamp before today (2026-10-20)

OPEN_SHARE = 0.25     # about one case in four is open
STALL_SHARE = 0.25    # share of closed cases with a stall in Stages 2 to 4
DOC_SHARE = 0.7       # share of cases with documents attached

STALL_COMMENTS = [
    "Stalled: missing tax returns (W2/1099). Requested via RM.",
    "Stalled in underwriting due to missing income proof.",
    "Delayed: awaiting income verification.",
    "Stalled: LTV exceeds limit, referred to credit committee.",
    "Delayed: title report backlog.",
    "Stalled: paystub mismatch, client asked to resubmit.",
]


def build_case(n: int, rng: random.Random, cols: list[str]) -> dict:
    case_no = FIRST_NEW_ID + n - 1
    rtype, sub = rng.choice(SUBTYPES)
    is_open = rng.random() < OPEN_SHARE
    last_stage = rng.choice([1, 2, 3, 4]) if is_open else 5
    p = rng.choice(["P1", "P2"])
    fico, ltv, dti = rng.randint(620, 800), rng.randint(55, 90), rng.randint(25, 50)
    lvl, d = rng.randint(1, 3), rng.randint(1, 9)

    span_hours = int((DATE_TO - DATE_FROM).total_seconds() // 3600)
    start = DATE_FROM + timedelta(hours=rng.randint(0, span_hours))

    gaps = [rng.randint(4, 96) for _ in range(4)]
    if rng.random() < 0.15:
        gaps[rng.randint(1, 3)] = rng.randint(120, 300)  # some long holds
    ts = [start]
    for g in gaps[: last_stage - 1]:
        ts.append(ts[-1] + timedelta(hours=g))

    comments = {}
    for k in range(1, last_stage + 1):
        if k == 5:
            text = rng.choice(CLOSING)
        elif is_open and k == last_stage:
            text = rng.choice(OPEN_CURRENT)
        else:
            text = rng.choice(STAGE_POOLS[k])
        comments[k] = text.format(p=p, fico=fico, ltv=ltv, dti=dti, lvl=lvl, d=d)

    # Stalls in Stages 2 to 4 that the case moved past (closed cases) or is still stuck in (open cases).
    stall_stages = [k for k in (2, 3, 4) if k < last_stage]
    if stall_stages and rng.random() < (0.5 if is_open else STALL_SHARE):
        comments[rng.choice(stall_stages)] = rng.choice(STALL_COMMENTS)

    row = {"Case_ID": f"CS-2026-{case_no}", "Client_ID": f"CL-{rng.randint(10000, 99999)}",
           "Specific_Type": rtype, "Specific_Sub_Type": sub}
    for k in range(1, 6):
        row[f"Stage_{k}_Timestamp"] = ts[k - 1].strftime(FMT) if k <= last_stage else ""
        row[f"Stage_{k}_Comments"] = comments.get(k, "")

    if is_open:
        row["Total_TAT_Hours"] = ""
    else:
        tat = (ts[4] - ts[0]).total_seconds() / 3600
        row["Total_TAT_Hours"] = f"{tat:.2f}".rstrip("0").rstrip(".")

    docs = rng.random() < DOC_SHARE
    row["Documents_Attached"] = "Yes" if docs else "No"
    row["SLA_Days"] = str(SLA_DAYS[sub])
    row["Document_Details"] = document_details(sub, closed=not is_open) if docs else ""

    first, surname = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    row["Client_Name"] = f"{first} {surname}"
    row["Account_Number"] = str(rng.randint(10**9, 10**10 - 1))
    row["Client_Email"] = f"{first.lower()}.{surname.lower()}{rng.randint(10, 99)}@example.com"
    row["Contact_Phone"] = f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
    row["Priority"] = priority_from_comments(row)
    row["Case_Status"] = "Open" if is_open else "Closed"
    return {c: row.get(c, "") for c in cols}


def main() -> None:
    df = pd.read_csv(CASES_CSV, dtype=str, keep_default_na=False)
    if (df["Case_ID"] == f"CS-2026-{FIRST_NEW_ID}").any():
        print("New cases already present; nothing changed.")
        return

    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before bulk cases).csv")
    shutil.copyfile(CASES_CSV, backup)

    rng = random.Random(2028)
    new = pd.DataFrame([build_case(n, rng, list(df.columns)) for n in range(1, COUNT + 1)], columns=df.columns)
    out = pd.concat([df, new], ignore_index=True)
    out.to_csv(CASES_CSV, index=False)
    open_count = int((new["Case_Status"] == "Open").sum())
    print(f"Added {len(new)} cases ({open_count} open, {len(new) - open_count} closed). "
          f"Total now {len(out)}. Backup: {backup.name}")


if __name__ == "__main__":
    main()
