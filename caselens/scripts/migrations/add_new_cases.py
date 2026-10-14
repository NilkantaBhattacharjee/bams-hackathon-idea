"""One-time: append 50 SYNTHETIC cases (CS-2026-1101 to CS-2026-1150) to the case CSV.

15 cases are open and stop at Stage 1 to 4 (Stage 5 fields are left blank). 35 are closed.
All names, accounts, emails and phone numbers are fictional. Values are seeded so reruns match.
The script backs up the CSV first and does nothing if the new cases already exist.
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
from config import CASES_CSV  # noqa: E402

FMT = "%Y-%m-%d %H:%M:%S"
FIRST_NEW_ID = 1101
COUNT = 50

SUBTYPES = [
    ("Retail_Banking", "Mortgage_Refinance"), ("Retail_Banking", "Personal_Loan"),
    ("Commercial_Lending", "SME_Working_Capital"), ("Commercial_Lending", "Equipment_Financing"),
    ("Wealth_Management", "Portfolio_Transfer"), ("Wealth_Management", "Estate_Account_Opening"),
    ("Credit_Cards", "Fraud_Dispute"), ("Credit_Cards", "Credit_Limit_Increase"),
]

# Index numbers (1 to 50) that are open. Spread across the batch.
OPEN_IDX = {n for n in range(1, COUNT + 1) if n % 10 in (3, 7, 8)}

STAGE_POOLS = {
    1: ["Case logged via IB. Priority set to {p}.", "Portal submission received.",
        "Application received via RM.", "In-person branch submission."],
    2: ["KYC refreshed. PEP/SAN check clear.", "Bureau credit score pulled. FICO {fico}.",
        "Documents received. Verification started.", "KYC and AML docs verified. UBO identified."],
    3: ["LTV {ltv}%. DTI calculated at {dti}%.", "Underwriting review in progress.",
        "Financial statements analyzed. DSCR is 1.{d}x."],
    4: ["LOA Level {lvl} signed off by RM.", "Credit Committee approval granted. Conditions set.",
        "Decision engine rule DE-4 applied.", "Sign-off received from Credit Risk Head."],
}
DELAYED_STAGE_3 = "Delayed: awaiting income verification."
OPEN_CURRENT = ["Awaiting proof of address.", "Awaiting credit committee decision.",
                "Pending RM sign-off.", "Awaiting income verification.", "Under review by underwriting."]
CLOSING = ["CBS updated. Case closed.", "Disbursed via wire transfer. Ticket closed.",
           "Account activated in core system. Case closed.", "Assets transferred successfully. Case closed.",
           "Funds credited to account. Case closed."]


def build_case(n: int, rng: random.Random, cols: list[str]) -> dict:
    case_no = FIRST_NEW_ID + n - 1
    rtype, sub = SUBTYPES[(n - 1) % len(SUBTYPES)]
    is_open = n in OPEN_IDX
    last_stage = rng.choice([1, 2, 3, 4]) if is_open else 5
    p = rng.choice(["P1", "P2"])
    fico, ltv, dti = rng.randint(620, 800), rng.randint(55, 90), rng.randint(25, 50)
    lvl, d = rng.randint(1, 3), rng.randint(1, 9)

    # Gaps between stage entries, in hours. Some closed cases get a long Stage 3 hold-up.
    gaps = [rng.randint(4, 96) for _ in range(4)]
    delayed = not is_open and rng.random() < 0.3
    if delayed:
        gaps[2] = rng.randint(120, 260)
    start = datetime(2026, 4, 1) + timedelta(hours=rng.randint(0, 24 * 20))
    ts = [start]
    for g in gaps[: last_stage - 1]:
        ts.append(ts[-1] + timedelta(hours=g))

    comments = {}
    for k in range(1, last_stage + 1):
        if k == 5:
            text = rng.choice(CLOSING)
        elif is_open and k == last_stage:
            text = rng.choice(OPEN_CURRENT)
        elif k == 3 and delayed:
            text = DELAYED_STAGE_3
        else:
            text = rng.choice(STAGE_POOLS[k])
        comments[k] = text.format(p=p, fico=fico, ltv=ltv, dti=dti, lvl=lvl, d=d)

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

    docs = rng.random() < 0.7
    row["Documents_Attached"] = "Yes" if docs else "No"
    row["SLA_Days"] = str(SLA_DAYS[sub])
    row["Document_Details"] = document_details(sub, closed=not is_open) if docs else ""

    first, surname = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    row["Client_Name"] = f"{first} {surname}"
    row["Account_Number"] = str(rng.randint(10**9, 10**10 - 1))
    row["Client_Email"] = f"{first.lower()}.{surname.lower()}{rng.randint(10, 99)}@example.com"
    row["Contact_Phone"] = f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
    row["Priority"] = priority_from_comments(row)
    return {c: row.get(c, "") for c in cols}


def main() -> None:
    df = pd.read_csv(CASES_CSV, dtype=str, keep_default_na=False)
    if (df["Case_ID"] == f"CS-2026-{FIRST_NEW_ID}").any():
        print("New cases already present; nothing changed.")
        return

    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before new cases).csv")
    shutil.copyfile(CASES_CSV, backup)

    rng = random.Random(2027)
    new = pd.DataFrame([build_case(n, rng, list(df.columns)) for n in range(1, COUNT + 1)], columns=df.columns)
    out = pd.concat([df, new], ignore_index=True)
    out.to_csv(CASES_CSV, index=False)
    open_count = int((new["Total_TAT_Hours"] == "").sum())
    print(f"Added {len(new)} cases ({open_count} open, {len(new) - open_count} closed). Backup: {backup.name}")


if __name__ == "__main__":
    main()
