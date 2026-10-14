"""Deterministic metrics computed from case timestamps.

Stage N's entry time is Stage_N_Timestamp. A stage's duration is the time from its
entry to the next stage's entry. Stage 5 has no exit, so only the total TAT covers it.
"""

import pandas as pd

from config import CASES_CSV

STAGES = 5


def load_cases(path=CASES_CSV) -> pd.DataFrame:
    """Load the case CSV and parse stage timestamps. Unparseable values become NaT."""
    df = pd.read_csv(path)
    for n in range(1, STAGES + 1):
        col = f"Stage_{n}_Timestamp"
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def stage_durations(df: pd.DataFrame) -> pd.DataFrame:
    """Hours spent in Stages 1 to 4. Negative values mean timestamps are out of order."""
    parts = []
    for n in range(1, STAGES):
        hours = (df[f"Stage_{n + 1}_Timestamp"] - df[f"Stage_{n}_Timestamp"]).dt.total_seconds() / 3600
        parts.append(pd.DataFrame({"Case_ID": df["Case_ID"], "Stage": n, "Hours": hours}))
    return pd.concat(parts, ignore_index=True)


def total_tat_hours(df: pd.DataFrame) -> pd.Series:
    """Total TAT used by the metrics: the stored Total_TAT_Hours value."""
    return df["Total_TAT_Hours"].astype(float)


def recalculated_tat_hours(df: pd.DataFrame) -> pd.Series:
    """Hours from Stage 1 entry to Stage 5 entry, recalculated from timestamps (used for validation)."""
    return (df["Stage_5_Timestamp"] - df["Stage_1_Timestamp"]).dt.total_seconds() / 3600


def bottleneck_per_case(df: pd.DataFrame) -> pd.DataFrame:
    """The longest valid stage (Stages 1 to 4) for each case."""
    d = stage_durations(df).dropna(subset=["Hours"])
    d = d[d["Hours"] >= 0]
    idx = d.groupby("Case_ID")["Hours"].idxmax()
    return d.loc[idx].reset_index(drop=True)
