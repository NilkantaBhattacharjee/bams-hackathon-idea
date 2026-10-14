from pathlib import Path

# Repository root: bpm-case-copilot/
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = Path(__file__).resolve().parent / "syntheticData"
CASES_CSV = DATA_DIR / "Financial_BPM_Cases_100 - Untitled.csv"
JARGON_JSON = DATA_DIR / "financial_jargon_dictionary.json"
REPORT_PATH = Path(__file__).resolve().parent / "reports" / "data_validation.md"
JARGON_REPORT_PATH = Path(__file__).resolve().parent / "reports" / "jargon_lookup.md"

# Stored Total_TAT_Hours is compared with the recalculated value using this tolerance.
TAT_TOLERANCE_HOURS = 0.01
