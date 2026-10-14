"""One-time: add SLA and document fields to the case CSV.

The values are SYNTHETIC placeholders, chosen per sub-type so the case card can be shown.
Replace them with real values from your BPM system when available.
The script backs up the original file first and does nothing if the fields already exist.
"""

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # project root, for config and summary
from config import CASES_CSV  # noqa: E402
from summary import is_closed  # noqa: E402

SLA_DAYS = {
    "Mortgage_Refinance": 7,
    "Personal_Loan": 3,
    "SME_Working_Capital": 7,
    "Equipment_Financing": 5,
    "Portfolio_Transfer": 3,
    "Estate_Account_Opening": 5,
    "Fraud_Dispute": 10,
    "Credit_Limit_Increase": 2,
}

DOCUMENTS = {
    "Mortgage_Refinance": ["Passport", "Proof of Address", "Tax Returns (W2/1099)"],
    "Personal_Loan": ["Passport", "Paystub", "Bank Statement"],
    "SME_Working_Capital": ["Tax ID Certificate", "Financial Statements", "KYC Documents"],
    "Equipment_Financing": ["Equipment Invoice", "Asset Valuation Report"],
    "Portfolio_Transfer": ["Account Statement", "Transfer Form"],
    "Estate_Account_Opening": ["Death Certificate", "Letters Testamentary", "Notarized Form"],
    "Fraud_Dispute": ["Dispute Form", "Transaction Statement"],
    "Credit_Limit_Increase": ["Income Proof"],
}


def document_details(sub_type: str, closed: bool) -> str:
    """Name:Status pairs joined by '|'. Closed cases are fully validated; open cases leave the last one pending."""
    names = DOCUMENTS.get(sub_type, ["Supporting Document"])
    parts = []
    for i, name in enumerate(names):
        status = "Validated" if closed or i < len(names) - 1 else "Pending"
        parts.append(f"{name}:{status}")
    return "|".join(parts)


def main() -> None:
    df = pd.read_csv(CASES_CSV, dtype=str, keep_default_na=False)
    if "SLA_Days" in df.columns:
        print("Fields already present; nothing changed.")
        return

    backup = CASES_CSV.with_name(CASES_CSV.stem + " (before fields).csv")
    shutil.copyfile(CASES_CSV, backup)

    df["SLA_Days"] = df["Specific_Sub_Type"].map(SLA_DAYS).fillna("")
    df["Document_Details"] = [
        document_details(row.Specific_Sub_Type, is_closed(row.Stage_5_Comments))
        if row.Documents_Attached == "Yes" else ""
        for row in df.itertuples()
    ]
    df.to_csv(CASES_CSV, index=False)
    print(f"Added SLA_Days and Document_Details to {len(df)} rows. Backup: {backup.name}")


if __name__ == "__main__":
    main()
