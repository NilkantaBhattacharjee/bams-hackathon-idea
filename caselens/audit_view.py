"""Read the audit log and summarise it for the Audit view page. Reads the JSONL file only.

Each line is written by guardrails.audit(). Template answers make no model call, so they have no
latency or token count. Those are shown as blank, never as zero.
"""

import json
from pathlib import Path

import pandas as pd

from guardrails import LOG_PATH

COLUMNS = ["ts", "kind", "model", "prompt_version", "case_ids", "citations", "dropped_lines",
           "error", "latency_ms", "total_tokens", "summary_id"]


def load_log(path: Path | None = None) -> pd.DataFrame:
    """All audit events as a DataFrame. Empty frame with the right columns if the log is missing."""
    path = Path(path or LOG_PATH)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a damaged line is skipped, not guessed
    df = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce", utc=True)
    df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce")
    df["total_tokens"] = pd.to_numeric(df["total_tokens"], errors="coerce")
    df["dropped_lines"] = pd.to_numeric(df["dropped_lines"], errors="coerce").fillna(0).astype(int)
    return df[COLUMNS].sort_values("ts", ascending=False).reset_index(drop=True)


def cost_per_call(df: pd.DataFrame, price_per_1k: float) -> pd.Series:
    """Estimated USD per model call: total tokens / 1000 x price. Blank where no token count was logged."""
    return df["total_tokens"] / 1000.0 * price_per_1k


def model_events(df: pd.DataFrame) -> pd.DataFrame:
    """Events that called a model (have a model name). Template-only events are excluded from averages."""
    return df[df["model"].fillna("") != ""]


def summary(df: pd.DataFrame) -> dict:
    """Headline numbers for the page. Averages use only events with a measured latency or token count."""
    model = model_events(df)
    lat = model["latency_ms"].dropna()
    tok = model["total_tokens"].dropna()
    blocked_mask = df["kind"].fillna("").str.contains("blocked|refused|pii", case=False)
    error_mask = (df["error"].fillna("") != "") & ~blocked_mask
    return {
        "events": len(df),
        "model_calls": len(model),
        "errors": int(error_mask.sum()),
        "blocked": int(blocked_mask.sum()),
        "dropped_lines": int(df["dropped_lines"].sum()),
        "avg_latency_ms": round(float(lat.mean()), 0) if len(lat) else None,
        "p95_latency_ms": round(float(lat.quantile(0.95)), 0) if len(lat) else None,
        "total_tokens": int(tok.sum()) if len(tok) else None,
        "avg_tokens_per_call": round(float(tok.mean()), 0) if len(tok) else None,
    }


def by_kind(df: pd.DataFrame) -> pd.DataFrame:
    """Counts and average latency and tokens for each event kind."""
    if df.empty:
        return pd.DataFrame(columns=["kind", "events", "avg_latency_ms", "avg_tokens"])
    out = df.groupby("kind").agg(
        events=("kind", "count"),
        avg_latency_ms=("latency_ms", "mean"),
        avg_tokens=("total_tokens", "mean"),
    ).reset_index()
    out["avg_latency_ms"] = out["avg_latency_ms"].round(0)
    out["avg_tokens"] = out["avg_tokens"].round(0)
    return out


def by_prompt_version(df: pd.DataFrame) -> pd.DataFrame:
    """Latency, tokens, and dropped lines per prompt version, for comparing prompt changes."""
    if df.empty:
        return pd.DataFrame(columns=["prompt_version", "events", "model_calls", "avg_latency_ms",
                                     "avg_tokens", "dropped_lines"])
    d = df.assign(prompt_version=df["prompt_version"].fillna("unknown"),
                  _is_model=df["model"].fillna("") != "")
    out = d.groupby("prompt_version").agg(
        events=("kind", "count"),
        model_calls=("_is_model", "sum"),
        avg_latency_ms=("latency_ms", "mean"),
        avg_tokens=("total_tokens", "mean"),
        dropped_lines=("dropped_lines", "sum"),
    ).reset_index()
    out["avg_latency_ms"] = out["avg_latency_ms"].round(0)
    out["avg_tokens"] = out["avg_tokens"].round(0)
    return out


def cost_by_summary(df: pd.DataFrame, price_per_1k: float) -> pd.DataFrame:
    """Estimated cost per summary card: all model calls tagged with the same summary_id."""
    empty = pd.DataFrame(columns=["summary_id", "case_id", "calls", "total_tokens", "est_cost_usd"])
    if price_per_1k <= 0 or df.empty or "summary_id" not in df.columns:
        return empty
    m = model_events(df)
    m = m[m["summary_id"].fillna("") != ""].copy()
    if m.empty:
        return empty
    m["total_tokens"] = pd.to_numeric(m["total_tokens"], errors="coerce").fillna(0)
    m["case_id"] = m["case_ids"].map(lambda ids: ids[0] if isinstance(ids, (list, tuple)) and ids else "")
    g = m.groupby("summary_id").agg(
        case_id=("case_id", "first"),
        calls=("total_tokens", "count"),
        total_tokens=("total_tokens", "sum"),
    ).reset_index()
    g["est_cost_usd"] = (g["total_tokens"] / 1000.0 * price_per_1k).round(5)
    return g.sort_values("est_cost_usd", ascending=False).reset_index(drop=True)


def cost_by_case(df: pd.DataFrame, price_per_1k: float) -> pd.DataFrame:
    """Estimated cost per case ID, from every model call that named that case.
    A summary call names one case; chat and trend calls may name none or several."""
    if price_per_1k <= 0 or df.empty:
        return pd.DataFrame(columns=["case_id", "calls", "total_tokens", "est_cost_usd"])
    m = model_events(df)[["case_ids", "total_tokens"]].copy()
    m["total_tokens"] = pd.to_numeric(m["total_tokens"], errors="coerce")
    m = m.dropna(subset=["total_tokens"])
    rows = []
    for ids, tok in zip(m["case_ids"], m["total_tokens"]):
        ids = list(ids) if isinstance(ids, (list, tuple)) else []
        for cid in ids:
            rows.append({"case_id": cid, "total_tokens": tok})
    if not rows:
        return pd.DataFrame(columns=["case_id", "calls", "total_tokens", "est_cost_usd"])
    g = pd.DataFrame(rows).groupby("case_id").agg(
        calls=("total_tokens", "count"), total_tokens=("total_tokens", "sum")).reset_index()
    g["est_cost_usd"] = (g["total_tokens"] / 1000.0 * price_per_1k).round(5)
    return g.sort_values("est_cost_usd", ascending=False).reset_index(drop=True)


def feedback_summary(df: pd.DataFrame) -> dict:
    """Thumbs up and down counts from feedback events, and the share that were positive."""
    fb = df[df["kind"].fillna("") == "feedback"]
    up = int((fb["error"].fillna("") == "up").sum())
    down = int((fb["error"].fillna("") == "down").sum())
    total = up + down
    return {"up": up, "down": down, "total": total,
            "helpful_share": (up / total) if total else None}


def filter_log(df: pd.DataFrame, kinds=None, models=None, start=None, end=None) -> pd.DataFrame:
    """Narrow the log by kind, model, and date (UTC date range, inclusive). Blank means no filter."""
    mask = pd.Series(True, index=df.index)
    if kinds:
        mask &= df["kind"].isin(kinds)
    if models:
        mask &= df["model"].isin(models)
    if start is not None:
        mask &= df["ts"].dt.date >= start
    if end is not None:
        mask &= df["ts"].dt.date <= end
    return df[mask].reset_index(drop=True)
