"""SLA breaches and date bases for list views. Reads the CSV only, no model call.

Breach rule: a closed case breaches when its Total_TAT_Hours is more than SLA_Days x 24.
Open cases are not breaches yet. They are shown separately as "open, past SLA" when their age
(from creation to the report date) is already over SLA_Days.
Closed date: the Stage 5 timestamp, the point the case reached its final stage.
"""

import pandas as pd

import summary


def sla_hours(df: pd.DataFrame) -> pd.Series:
    """SLA target in hours. NaN where SLA_Days is not recorded."""
    return pd.to_numeric(df["SLA_Days"], errors="coerce") * 24


def closed_flags(df: pd.DataFrame) -> pd.Series:
    return pd.Series(
        [summary.closed_status(row, row["Stage_5_Comments"]) for _, row in df.iterrows()],
        index=df.index,
    )


def breach_table(df: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per case past its SLA. Closed breaches first, then open cases already past SLA."""
    as_of = as_of or pd.Timestamp.now().normalize()
    closed = closed_flags(df)
    target = sla_hours(df)
    tat = pd.to_numeric(df["Total_TAT_Hours"], errors="coerce")
    created = df["Stage_1_Timestamp"]
    age = (as_of - created).dt.total_seconds() / 3600

    closed_breach = closed & (tat > target)
    open_breach = (~closed) & (age > target)

    rows = []
    for idx in df.index[closed_breach | open_breach]:
        is_closed = bool(closed[idx])
        hours = tat[idx] if is_closed else age[idx]
        rows.append({
            "Case_ID": df.at[idx, "Case_ID"],
            "Type": df.at[idx, "Specific_Type"],
            "Sub_type": df.at[idx, "Specific_Sub_Type"],
            "Priority": df.at[idx, "Priority"] if "Priority" in df.columns else "",
            "Status": "Closed" if is_closed else "Open",
            "SLA_days": int(target[idx] / 24),
            "Hours": round(float(hours), 1),
            "Over_by_hours": round(float(hours - target[idx]), 1),
        })
    out = pd.DataFrame(rows, columns=["Case_ID", "Type", "Sub_type", "Priority", "Status",
                                      "SLA_days", "Hours", "Over_by_hours"])
    if out.empty:
        return out
    out["_closed"] = (out["Status"] == "Closed").astype(int)
    out = out.sort_values(["_closed", "Over_by_hours"], ascending=[False, False]).drop(columns="_closed")
    return out.reset_index(drop=True)


def in_range(df: pd.DataFrame, column: str, start, end) -> pd.Series:
    """Rows whose date in `column` falls between start and end, inclusive. Blank dates are excluded."""
    d = df[column].dt.date
    return (d >= start) & (d <= end) & d.notna()


def closed_dates(df: pd.DataFrame) -> pd.Series:
    """Closed date per case: the Stage 5 timestamp for closed cases, NaT otherwise."""
    closed = closed_flags(df)
    return df["Stage_5_Timestamp"].where(closed)


def month_options(series: pd.Series) -> list[str]:
    """'YYYY-MM' labels for every month that has at least one date, newest first."""
    months = series.dropna().dt.to_period("M").astype(str).unique().tolist()
    return sorted(months, reverse=True)
