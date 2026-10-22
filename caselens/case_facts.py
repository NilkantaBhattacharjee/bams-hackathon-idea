"""Exact answers about one case, computed from the CSV. No model call.

Covers: current stage, time taken to reach each stage, total time, open or closed,
documents attached and their status, SLA target, and the stall history.
"""

import re

import pandas as pd

import summary
from metrics import total_tat_hours

STAGE_WORDS = {
    "ingestion": 1, "triage": 1, "triaging": 1, "verification": 2, "verify": 2,
    "assessment": 3, "underwriting": 3, "decisioning": 4, "approval": 4,
    "fulfillment": 5, "fulfilment": 5, "resolution": 5,
}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}

TIME_Q = re.compile(r"\b(how long|how much time|time taken|duration|took|take|tat|turnaround)\b", re.I)
DOC_Q = re.compile(r"\b(document|documents|attached|attachment|passport|proof|paperwork|files?)\b", re.I)
STAGE_Q = re.compile(r"\b(stage|which stage|what stage|current stage|at which)\b", re.I)
STATUS_Q = re.compile(r"\b(closed|open|resolved|status|still|finished|completed)\b", re.I)
SLA_Q = re.compile(r"\b(sla|deadline|target|breach)\b", re.I)
STALL_Q = re.compile(r"\b(stall|stalled|delay|delayed|hold|stuck|why)\b", re.I)


def stage_entry_text(df, cid: str, n: int) -> str:
    """Date the case entered Stage n, from the CSV timestamp."""
    row = df[df["Case_ID"] == cid].iloc[0]
    ts = row[f"Stage_{n}_Timestamp"]
    return ts.strftime("%d-%b-%Y %H:%M")


CASE_PLURAL = re.compile(r"\b(cases|case ids?|caseids?|case-ids?)\b", re.IGNORECASE)
LIST_WORD = re.compile(
    r"\b(list|which|mention|show|few|some|all|name|give me|tell me|how many|count|number of)\b",
    re.IGNORECASE,
)
STALL_LIST = re.compile(r"\b(stall|stalls|stalled|delay|delayed|stuck|on hold)\b", re.IGNORECASE)
OPEN_WORD = re.compile(r"\b(still|open|ongoing|pending|unresolved|not closed)\b", re.IGNORECASE)
CLOSED_WORD = re.compile(r"\b(closed|resolved|completed|finished)\b", re.IGNORECASE)
ANY_CASE_ID = re.compile(r"\bCS-\d{4}-\d{4}\b", re.IGNORECASE)
MAX_LIST = 10
# Document names as stored in Document_Details. The group 'identification' covers identity-type documents.
DOC_NAME_ALIASES = {
    "passport": ["Passport"],
    "identification": ["Passport", "Tax ID Certificate", "Death Certificate"],
    "identity": ["Passport", "Tax ID Certificate", "Death Certificate"],
    "id document": ["Passport", "Tax ID Certificate", "Death Certificate"],
    "tax id": ["Tax ID Certificate"],
    "death certificate": ["Death Certificate"],
    "paystub": ["Paystub"],
    "pay stub": ["Paystub"],
    "bank statement": ["Bank Statement"],
    "proof of address": ["Proof of Address"],
}


def doc_name_filter(question: str) -> list[str] | None:
    """Document names the question asks about, or None if no document name is named."""
    q = (question or "").lower()
    for alias in sorted(DOC_NAME_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", q):
            return DOC_NAME_ALIASES[alias]
    return None


DOCS_YES = re.compile(r"\b(with|have|has|attached|attachments?)\b.*\bdocuments?\b|\bdocuments? attached\b", re.I)
DOCS_NO = re.compile(r"\b(no|without|not|missing)\b.*\bdocuments?\b", re.I)
PRIORITY_Q = re.compile(r"\b(p1|p2|priority)\b", re.I)
CLIENT_WAIT_Q = re.compile(r"\b(waiting|wait|needed|needs?)\b.*\b(client|customer)\b|\b(client|customer)\b.*\b(action|waiting|needed)\b", re.I)


VERIFY_Q = re.compile(r"\b(are|is|were|was)\b.*\b(all|these|those|them|they)\b", re.IGNORECASE)


def subtype_filter(question: str, df) -> tuple[str, str] | None:
    """(column, value) for a sub-type or type named in the question, e.g. 'personal loan'. None if absent."""
    q = (question or "").lower().replace("_", " ")
    for col in ("Specific_Sub_Type", "Specific_Type"):
        values = sorted(df[col].unique(), key=len, reverse=True)  # longest first, so 'credit card' wins
        for value in values:
            if re.search(r"\b" + re.escape(value.lower().replace("_", " ")) + r"\b", q):
                return col, value
    return None


def previous_case_ids(history) -> list[str]:
    """Case IDs named in the most recent assistant answer."""
    for msg in reversed(history or []):
        if msg.get("role") == "assistant":
            return list(dict.fromkeys(ANY_CASE_ID.findall(str(msg.get("content", "")).upper())))
    return []


def previous_truncated(history) -> bool:
    for msg in reversed(history or []):
        if msg.get("role") == "assistant":
            return "Showing the first" in str(msg.get("content", ""))
    return False


def verify_text(ids: list[str], ftr: tuple[str, str], df, truncated: bool = False) -> str:
    """Check each listed case against a sub-type or type. Uses the CSV, not the model."""
    col, value = ftr
    label = value.replace("_", " ")
    field = dict(zip(df["Case_ID"], df[col]))
    checked = [c for c in ids if c in field]
    if not checked:
        return "There are no cases from the previous answer to check. Ask for the list first."
    note = " Only the cases shown in the previous answer were checked." if truncated else ""
    miss = [c for c in checked if field[c] != value]
    if not miss:
        return f"Yes. All {len(checked)} cases listed above are {label} cases.{note}"
    lines = [f"No. {len(checked) - len(miss)} of {len(checked)} cases listed above are {label} cases.{note}",
             "Not " + label + ":"]
    lines += [f"- {c} | {field[c].replace('_', ' ')}" for c in miss]
    return "\n".join(lines)


DOC_ASK = re.compile(
    r"\b(documents?|paperwork|files?|proof)\b"
    r".*\b(needed|needs?|required|require[sd]?|for|usually|typically|should|must)\b"
    r"|\b(needed|needs?|required|require[sd]?|for|usually|typically|should|must)\b.*\b(documents?|paperwork|files?|proof)\b",
    re.IGNORECASE,
)


def subtype_docs_text(question: str, ftr, df, patterns) -> str | None:
    """Documents recorded on cases of a named sub-type or type, with counts. Reads the CSV only."""
    if not ftr or not DOC_ASK.search(question or ""):
        return None
    col, value = ftr
    label = value.replace("_", " ")
    counts: dict[str, int] = {}
    total = 0
    for cid in df["Case_ID"]:
        if df.loc[df["Case_ID"] == cid, col].iloc[0] != value:
            continue
        total += 1
        f = summary.case_facts(df, cid, patterns)
        for name in dict.fromkeys(n for n, _ in doc_items(f)):
            counts[name] = counts.get(name, 0) + 1
    if total == 0:
        return f"No cases are recorded for {label}."
    if not counts:
        return (f"No documents are recorded on the {total} {label} case(s). "
                "The case records do not list a document requirement.")
    lines = [f"Documents recorded on {total} {label} case(s):"]
    lines += [f"- {name}: on {n} of {total} cases" for name, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    lines.append("This is based on the documents attached to past cases, not a policy list.")
    return "\n".join(lines)


def list_cases(question: str, df, patterns) -> str | None:
    """List cases matching a sub-type or type, and/or a stall or open/closed filter. None if not a list request."""
    q = question or ""
    if ANY_CASE_ID.search(q) or not CASE_PLURAL.search(q) or not LIST_WORD.search(q):
        return None
    ftr = subtype_filter(q, df)
    want_stall = bool(STALL_LIST.search(q))
    want_open = bool(OPEN_WORD.search(q))
    want_closed = bool(CLOSED_WORD.search(q))
    status_filter = want_open != want_closed  # both, or neither, means no status filter
    docs_yes = bool(DOCS_YES.search(q)) and not DOCS_NO.search(q)
    docs_no = bool(DOCS_NO.search(q))
    doc_names = doc_name_filter(q)
    if doc_names:
        docs_yes = True
    prio = re.search(r"\bP([12])\b", q, re.I)
    want_client = bool(CLIENT_WAIT_Q.search(q))
    stage_num = None
    stage_m = re.search(r"\bstage\s*([1-5])\b", q, re.I)
    if stage_m:
        stage_num = int(stage_m.group(1))

    rows = []
    for cid in df["Case_ID"]:
        f = summary.case_facts(df, cid, patterns)
        if ftr and f["sub_type"] != ftr[1] and ftr[0] == "Specific_Sub_Type":
            continue
        if ftr and f["type"] != ftr[1] and ftr[0] == "Specific_Type":
            continue
        if docs_yes and f["documents"] != "Yes":
            continue
        if doc_names and not any(name in [n for n, _ in doc_items(f)] for name in doc_names):
            continue
        if docs_no and f["documents"] == "Yes":
            continue
        if prio and str(df.loc[df["Case_ID"] == cid, "Priority"].iloc[0]) != f"P{prio.group(1)}":
            continue
        if want_client and not (not f["closed"] and any(s == "Pending" for _, s in doc_items(f))):
            continue
        if stage_num is not None:
            if want_stall and stage_num not in f["stalls"]:
                continue
            if not want_stall and not f["closed"] and current_stage(f) != stage_num:
                continue
            if not want_stall and f["closed"]:
                continue
        if want_stall and not f["stalls"]:
            continue
        if status_filter and want_open and f["closed"]:
            continue
        if status_filter and want_closed and not f["closed"]:
            continue
        rows.append((cid, f))

    desc = []
    if ftr:
        desc.append(ftr[1].replace("_", " "))
    if doc_names:
        desc.append("with " + " or ".join(doc_names).lower())
    elif docs_yes:
        desc.append("with documents")
    if docs_no:
        desc.append("without documents")
    if prio:
        desc.append(f"P{prio.group(1)}")
    if want_client:
        desc.append("waiting for the client")
    if stage_num is not None:
        desc.append(f"at stage {stage_num}")
    if want_stall:
        desc.append("stalled")
    if status_filter:
        desc.append("still open" if want_open else "closed")
    label = " and ".join(desc)
    total = len(rows)
    if desc and not rows:
        return f"No cases are {label}."

    shown = rows[:MAX_LIST]
    head = f"{total} case(s) {label}:" if desc else f"Showing {len(shown)} of {total} cases:"
    lines = [head]
    for cid, f in shown:
        status = "Closed" if f["closed"] else "Open"
        stall = ", ".join(f"Stage {n}" for n in f["stalls"]) or "none"
        ctype = f['type'].replace('_', ' ')
        sub = f['sub_type'].replace('_', ' ')
        lines.append(f"- {cid} | {ctype} / {sub} | Stall: {stall} | Status: {status}")
    if total > MAX_LIST:
        lines.append(f"Showing the first {MAX_LIST} of {total}. Ask for a narrower filter to see the rest.")
    return "\n".join(lines)


def hours_text(h: float) -> str:
    if h < 24:
        return f"{h:.1f} hours"
    return f"{h / 24:.1f} days ({h:.1f} hours)"


def stage_entry_hours(df, cid: str, n: int) -> float:
    """Hours from case creation (Stage 1 entry) to Stage n entry."""
    row = df[df["Case_ID"] == cid].iloc[0]
    start = row["Stage_1_Timestamp"]
    return float((row[f"Stage_{n}_Timestamp"] - start).total_seconds() / 3600)


def documents_text(f) -> str:
    if f["documents"] != "Yes":
        return "No documents are attached to this case."
    lines = summary.doc_lines(f)
    return "Documents attached:\n" + "\n".join(f"- {line}" for line in lines)


NEED_Q = re.compile(
    r"\b(needed|needs?|require[sd]?|requirements?|proceed|provide|outstanding|next step|next action|"
    r"to close|closure)\b",
    re.I,
)
EXTRA_DOC_Q = re.compile(
    r"\b(additional|more|extra|missing|further|pending)\b.*\bdocuments?\b"
    r"|\bdocuments?\b.*\b(additional|more|extra|missing|pending|required|needed)\b",
    re.I,
)
LONG_Q = re.compile(
    r"\b(long|slow|took|taken|takes|take)\b"
    r"|\bwhy\b.*\b(close|closed|closure|complete|completed|finish|finished)\b",
    re.I,
)


def doc_items(f) -> list[tuple[str, str]]:
    """(document name, Validated or Pending) pairs from Document_Details."""
    out = []
    for item in f["doc_details"].split("|"):
        if ":" in item:
            name, status = item.rsplit(":", 1)
            out.append((name.strip(), status.strip()))
    return out


def current_stage(f) -> int:
    """Latest stage with a comment."""
    filled = [n for n in range(1, 6) if f["comments"][n].strip()]
    return max(filled) if filled else 1


def pending_docs_text(f) -> str:
    if f["documents"] != "Yes" or not doc_items(f):
        return "No additional documents are required for this case."
    pending = [name for name, status in doc_items(f) if status == "Pending"]
    if pending:
        return "Additional documents still pending: " + ", ".join(pending) + "."
    return "No additional documents are required. All recorded documents are validated."


def client_needs_text(f) -> str:
    if f["closed"]:
        return "This case is closed. No action is needed from the client."
    stage = current_stage(f)
    lines = [f"The case is open at Stage {stage} ({summary.STAGE_NAMES[stage]})."]
    pending = [name for name, status in doc_items(f) if status == "Pending"]
    if pending:
        lines.append("Documents still needed from the client: " + ", ".join(pending) + ".")
    else:
        lines.append("No pending documents are recorded for the client.")
    latest = summary.mask(f["comments"][stage]).strip()
    if latest:
        lines.append(f"Latest update: {latest}")
    return "\n\n".join(lines)


def duration_text(f) -> str:
    if pd.isna(f["tat_hours"]):
        lines = ["Total turnaround is not final, because the case is still open."]
    else:
        lines = [f"Total turnaround: {hours_text(f['tat_hours'])}."]
    if f["bottleneck"]:
        n, hours = f["bottleneck"]
        lines.append(f"Longest stage: Stage {n} ({summary.STAGE_NAMES[n]}), {hours_text(hours)}.")
    if f["stalls"]:
        names = " and ".join(f"Stage {n} ({summary.STAGE_NAMES[n]})" for n in f["stalls"])
        lines.append(f"Stall recorded in {names}. The case later moved on.")
    else:
        lines.append("No stall was recorded for this case.")
    if not f["closed"]:
        lines.append("The case is still open, so it has not closed yet.")
    return "\n\n".join(lines)


REASON_OPEN_Q = re.compile(
    r"\b(reason|why)\b.*\b(open|pending|still|not closed|stalled)\b"
    r"|\b(open|pending)\b.*\b(reason|why)\b",
    re.I,
)


def open_reason_text(f) -> str:
    """Short, specific reason a case is open. No full summary."""
    if f["closed"]:
        return f"{f['case_id']} is closed, so it is not open."
    stage = current_stage(f)
    lines = [
        f"{f['case_id']} is open because it has not reached a final outcome. "
        f"Latest stage: Stage {stage} ({summary.STAGE_NAMES[stage]})."
    ]
    latest = summary.mask(f["comments"][stage]).strip()
    if latest:
        lines.append(f"Latest update: {latest}")
    pending = [name for name, status in doc_items(f) if status == "Pending"]
    if pending:
        lines.append("Documents still pending: " + ", ".join(pending) + ".")
    return "\n\n".join(lines)


STALL_REASON_Q = re.compile(
    r"\b(why|reason)\b.*\b(stall|stalled|stuck|delay|delayed)\b"
    r"|\b(stall|stalled|stuck|delay|delayed)\b.*\b(why|reason)\b",
    re.I,
)


def stall_reason_text(f) -> str:
    """Stalled stages with their recorded comments. Reads the CSV only."""
    if not f["stalls"]:
        return f"No stall was recorded for {f['case_id']}."
    lines = [f"{f['case_id']} was stalled in:"]
    for n in f["stalls"]:
        comment = summary.mask(f["comments"][n]).strip()
        lines.append(f"- Stage {n} ({summary.STAGE_NAMES[n]}): {comment}")
    if f["closed"]:
        lines.append("The case later moved on and closed.")
    else:
        lines.append("The case has moved on to a later stage, but is still open.")
    return "\n".join(lines)


RANK_Q = re.compile(r"\b(longest|slowest|most time|highest|maximum|max)\b", re.I)
CASE_WORD = re.compile(r"\bcases?\b", re.I)


SHORT_Q = re.compile(r"\b(shortest|fastest|quickest|least time|minimum|min)\b", re.I)
TOTAL_Q = re.compile(r"\b(total|overall|altogether|in all)\b|\bhow many cases\b|\bnumber of cases\b|\bcount of cases\b", re.I)
FILTER_WORDS = re.compile(
    r"\b(stall|stalled|delay|open|closed|still|pending|waiting|client|customer|document|documents|"
    r"p1|p2|priority|stage|with|without|no|missing|attached)\b",
    re.I,
)


def total_question(question: str, df) -> bool:
    """A plain 'how many cases in total' question with no filter in it."""
    q = question or ""
    return bool(TOTAL_Q.search(q)) and not FILTER_WORDS.search(q) and subtype_filter(q, df) is None


def total_text(df, patterns) -> str:
    closed = sum(1 for cid in df["Case_ID"] if summary.case_facts(df, cid, patterns)["closed"])
    total = len(df)
    return (f"There are {total} cases in total: {closed} closed and {total - closed} open.")


def ranking_text(df, patterns, n: int = 5, ascending: bool = False) -> str:
    """Closed cases ranked by total turnaround. Longest first by default; shortest first when ascending."""
    rows = []
    for cid in df["Case_ID"]:
        f = summary.case_facts(df, cid, patterns)
        if f["closed"] and not pd.isna(f["tat_hours"]):
            rows.append(f)
    rows.sort(key=lambda f: f["tat_hours"], reverse=not ascending)
    word = "shortest" if ascending else "longest"
    lines = [f"Closed cases with the {word} turnaround (top {min(n, len(rows))}):"]
    for f in rows[:n]:
        ctype = f["type"].replace("_", " ")
        sub = f["sub_type"].replace("_", " ")
        lines.append(f"- {f['case_id']} | {ctype} / {sub} | {hours_text(f['tat_hours'])}")
    return "\n".join(lines)


def answer_facts(question: str, cid: str, df, patterns) -> str | None:
    """Return an exact answer for a factual question about one case, or None if not a factual question."""
    f = summary.case_facts(df, cid, patterns)
    q = question.lower()
    if EXTRA_DOC_Q.search(q) or (NEED_Q.search(q) and DOC_Q.search(q)):
        return pending_docs_text(f)
    # 'how long / took ... to close' asks about time, not about what the client must do.
    names_stage = re.search(r"\bstage\s*[1-5]\b|\b(first|second|third|fourth|fifth)\b", q)
    if (re.search(r"\b(how long|took|take|taken|time)\b", q)
            and not re.search(r"\b(needed|needs?|require|provide)\b", q) and not names_stage):
        return duration_text(f)
    if NEED_Q.search(q):
        return client_needs_text(f)
    has_stage_ref = bool(re.search(r"\bstage\s*[1-5]\b|\b(first|second|third|fourth|fifth)\b", q))
    if LONG_Q.search(q) and not has_stage_ref:
        return duration_text(f)
    parts = []

    stage_match = None
    for word, n in STAGE_WORDS.items():
        if word in q:
            stage_match = n
    for word, n in ORDINALS.items():
        if re.search(rf"\b{word}\b", q):
            stage_match = n
    for m in re.finditer(r"\bstage\s*([1-5])\b", q):
        stage_match = int(m.group(1))

    if DOC_Q.search(q):
        parts.append(documents_text(f))
    if SLA_Q.search(q):
        sla = f["sla_days"]
        parts.append(f"SLA target: {sla} days." if sla is not None else "No SLA is recorded for this case.")
    # A specific stage asked about is answered first, before the general stage and status lines.
    if TIME_Q.search(q):
        if stage_match and stage_match > 1 and pd.isna(df[df["Case_ID"] == cid].iloc[0][f"Stage_{stage_match}_Timestamp"]):
            parts.append(
                f"Stage {stage_match} ({summary.STAGE_NAMES[stage_match]}) has not been reached yet, "
                f"so no time to reach it is recorded."
            )
        elif stage_match and stage_match > 1:
            parts.append(
                f"Time to reach Stage {stage_match} ({summary.STAGE_NAMES[stage_match]}): "
                f"{hours_text(stage_entry_hours(df, cid, stage_match))} from case creation."
            )
        elif stage_match == 1:
            parts.append("Stage 1 is the start of the case, so no time has elapsed to reach it.")
        else:
            parts.append(f"Total time from creation to the last recorded stage: {hours_text(f['tat_hours'])}.")
    if stage_match and not TIME_Q.search(q) and not DOC_Q.search(q):
        parts.insert(0, f"Stage {stage_match} ({summary.STAGE_NAMES[stage_match]}) of this case: "
                        f"entered {stage_entry_text(df, cid, stage_match)}.")
    if STAGE_Q.search(q) or (STATUS_Q.search(q) and not TIME_Q.search(q)):
        parts.append(f"Current stage: Stage 5 ({summary.STAGE_NAMES[5]}), the last stage recorded.")
        parts.append(f"Status: {'Closed' if f['closed'] else 'Open'}.")
    if STALL_Q.search(q):
        if f["stalls"]:
            names = " and ".join(f"Stage {n} ({summary.STAGE_NAMES[n]})" for n in f["stalls"])
            parts.append(f"Stalls were recorded in {names}. The case later moved on.")
        else:
            parts.append("No stall was recorded for this case.")

    if not parts:
        return None
    seen = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return "\n\n".join(seen)
