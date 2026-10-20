"""One-time: regenerate all 500 SYNTHETIC cases (CS-2026-1001 to CS-2026-1500) with realistic data.

- Stage times fall on weekdays, 09:00 to 17:00.
- Stage durations depend on the sub-type. SLA_Days is the target, and about 15% of closed cases breach it.
- Stage comments match their stage and the outcome. Open cases have no Stage 5 data.
- About 1 in 5 cases is open. Some cases have a stall in Stages 2 to 4.

Dry run by default (prints a summary). Pass --write to back up the CSV and save the new file.
All names, accounts, emails and phone numbers are fictional.
"""

import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, for config
from add_case_fields import document_details  # noqa: E402
from add_contact_fields import FIRST_NAMES, LAST_NAMES  # noqa: E402
from config import CASES_CSV  # noqa: E402

FMT = "%Y-%m-%d %H:%M:%S"
FIRST_ID = 1001
COUNT = 500
DATE_FROM = datetime(2024, 10, 21)
DATE_TO = datetime(2026, 9, 15)
OPEN_SHARE = 0.2
BREACH_SHARE = 0.15
DOC_SHARE = 0.7

# sub-type: (type, SLA days). The SLA days are also the planned duration basis.
PROFILE = {
    "Mortgage_Refinance": ("Retail_Banking", 10),
    "Personal_Loan": ("Retail_Banking", 4),
    "SME_Working_Capital": ("Commercial_Lending", 10),
    "Equipment_Financing": ("Commercial_Lending", 5),
    "Portfolio_Transfer": ("Wealth_Management", 3),
    "Estate_Account_Opening": ("Wealth_Management", 5),
    "Fraud_Dispute": ("Credit_Cards", 10),
    "Credit_Limit_Increase": ("Credit_Cards", 2),
}
CHANNELS = ["web portal", "RM referral", "branch", "mobile app", "broker"]
STAGE2 = ["KYC and AML checks completed.", "Documents received and verification started.",
          "Bureau check completed.", "Identity verified against source records."]
STAGE3 = ["Underwriting review in progress.", "Risk assessment completed.",
          "Income and collateral reviewed.", "Financial analysis completed."]
STAGE4 = ["Credit committee approval granted.", "Sign-off received from RM.",
          "Decision approved within authority limits.", "Approval recorded in decision system."]
STALL_COMMENTS = ["Stalled: awaiting income verification.",
                  "Stalled: missing documents requested from client.",
                  "Delayed: title report backlog.",
                  "Stalled: paystub mismatch, client asked to resubmit."]
OPEN_CURRENT = ["Awaiting client documents.", "Awaiting credit committee decision.",
                "Pending RM sign-off.", "Under review by underwriting."]
CLOSING = ["Funds disbursed. Case closed.", "Account activated. Case closed.",
           "Confirmation sent. Ticket closed."]


def to_business(ts: datetime) -> datetime:
    """Move a timestamp into weekday business hours (09:00 to 17:00)."""
    while True:
        if ts.weekday() >= 5:
            ts = (ts + timedelta(days=1)).replace(hour=9, minute=0)
        elif ts.hour < 9:
            ts = ts.replace(hour=9, minute=0)
        elif ts.hour >= 17:
            ts = (ts + timedelta(days=1)).replace(hour=9, minute=0)
        else:
            return ts


def build_case(n: int, rng: random.Random, cols: list[str]) -> dict:
    sub = rng.choice(list(PROFILE))
    rtype, sla_days = PROFILE[sub]
    is_open = rng.random() < OPEN_SHARE
    last = rng.choice([1, 2, 3, 4]) if is_open else 5
    priority = "P1" if rng.random() < 0.1 else "P2"
    channel = rng.choice(CHANNELS)

    # Duration: most cases finish inside SLA, about 15% run over it.
    # The stall adds 30% of the total after the gaps are split, so the base must stay below the target.
    factor = rng.uniform(1.05, 1.4) if rng.random() < BREACH_SHARE else rng.uniform(0.4, 0.75)
    total_hours = sla_days * 24 * factor
    weights = [rng.uniform(0.2, 1.0) for _ in range(4)]
    gaps = [total_hours * w / sum(weights) for w in weights]

    candidates = [k for k in (2, 3, 4) if k < last]
    stall = None
    if candidates and rng.random() < (0.35 if is_open else 0.15):
        stall = rng.choice(candidates)
        gaps[stall - 1] += total_hours * 0.3  # the stall adds time to that stage

    start = DATE_FROM + timedelta(days=rng.randint(0, (DATE_TO - DATE_FROM).days))
    start = to_business(start.replace(hour=rng.randint(9, 16), minute=rng.randint(0, 59)))
    # Business-hours shifts add time, so each stage is clipped and the total is kept near the planned hours.
    ts = [start]
    budget = total_hours
    for g in gaps[: last - 1]:
        step = min(g, budget)
        nxt = to_business(ts[-1] + timedelta(hours=step))
        ts.append(nxt)
        budget = max(budget - (nxt - ts[-2]).total_seconds() / 3600, 0)

    comments = {
        1: f"Case logged via {channel}. Priority set to {priority}.",
        2: rng.choice(STAGE2),
        3: rng.choice(STAGE3),
        4: rng.choice(STAGE4),
    }
    if stall:
        comments[stall] = rng.choice(STALL_COMMENTS)
    if is_open:
        comments[last] = rng.choice(OPEN_CURRENT)
    else:
        comments[5] = rng.choice(CLOSING)

    row = {"Case_ID": f"CS-2026-{FIRST_ID + n - 1}", "Client_ID": f"CL-{rng.randint(10000, 99999)}",
           "Specific_Type": rtype, "Specific_Sub_Type": sub}
    for k in range(1, 6):
        row[f"Stage_{k}_Timestamp"] = ts[k - 1].strftime(FMT) if k <= last else ""
        row[f"Stage_{k}_Comments"] = comments.get(k, "")
    row["Total_TAT_Hours"] = "" if is_open else f"{(ts[4] - ts[0]).total_seconds() / 3600:.2f}"

    docs = rng.random() < DOC_SHARE
    row["Documents_Attached"] = "Yes" if docs else "No"
    row["SLA_Days"] = str(sla_days)
    row["Document_Details"] = document_details(sub, closed=not is_open) if docs else ""

    first, surname = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    row["Client_Name"] = f"{first} {surname}"
    row["Account_Number"] = str(rng.randint(10**9, 10**10 - 1))
    row["Client_Email"] = f"{first.lower()}.{surname.lower()}{rng.randint(10, 99)}@example.com"
    row["Contact_Phone"] = f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
    row["Priority"] = priority
    row["Case_Status"] = "Open" if is_open else "Closed"
    return {c: row.get(c, "") for c in cols}


def summary_text(df: pd.DataFrame) -> str:
    closed = df["Case_Status"] == "Closed"
    tat = pd.to_numeric(df["Total_TAT_Hours"], errors="coerce")
    sla_h = pd.to_numeric(df["SLA_Days"], errors="coerce") * 24
    breach = int((closed & (tat > sla_h)).sum())
    stalled = int(df[["Stage_2_Comments", "Stage_3_Comments", "Stage_4_Comments"]]
                  .apply(lambda c: c.str.contains("Stalled|Delayed", na=False)).any(axis=1).sum())
    return (f"cases={len(df)} open={int((~closed).sum())} closed={int(closed.sum())} "
            f"stalled={stalled} sla_breach_closed={breach} ({breach / closed.sum():.0%} of closed)")


def main() -> None:
    cols = list(pd.read_csv(CASES_CSV, nrows=0).columns)
    rng = random.Random(2029)
    df = pd.DataFrame([build_case(n, rng, cols) for n in range(1, COUNT + 1)], columns=cols)
    print("Dry run:" if "--write" not in sys.argv else "Writing:", summary_text(df))
    if "--write" not in sys.argv:
        print("Run with --write to save. The current CSV is backed up first.")
        return
    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before realistic).csv")
    shutil.copyfile(CASES_CSV, backup)
    df.to_csv(CASES_CSV, index=False)
    print(f"Saved {len(df)} cases. Backup: {backup.name}")


if __name__ == "__main__":
    main()
