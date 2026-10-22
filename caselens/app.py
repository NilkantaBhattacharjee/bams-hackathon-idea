"""CaseLens Streamlit app: single-case summary and batch view."""

import pandas as pd
import streamlit as st

import audit_view
import chat
import scorecard
import export
import export_extra
import guardrails
import sla
import summary
import trends
from config import CASES_CSV, JARGON_JSON
from jargon import build_patterns, load_entries
from metrics import STAGES, bottleneck_per_case, load_cases, total_tat_hours


@st.cache_data
def get_cases() -> pd.DataFrame:
    return load_cases(CASES_CSV)


@st.cache_resource
def get_patterns():
    return build_patterns(load_entries(JARGON_JSON))


@st.cache_data
def get_entries() -> list[dict]:
    return load_entries(JARGON_JSON)


APP_CSS = """
<style>
/* Hero banner */
.cl-hero {
    background: linear-gradient(120deg, #6C5CE7 0%, #A29BFE 45%, #00CEC9 100%);
    color: #FFFFFF;
    border-radius: 16px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(108, 92, 231, 0.25);
    animation: cl-fade-in 0.6s ease-out;
}
.cl-hero h1 { color: #FFFFFF; margin: 0; font-size: 2.1rem; }
.cl-hero p { margin: 0.25rem 0 0 0; opacity: 0.92; }

/* Metric cards */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E6E8F2;
    border-left: 5px solid #6C5CE7;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    box-shadow: 0 2px 8px rgba(31, 36, 48, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(108, 92, 231, 0.18);
}
[data-testid="stMetricValue"] { color: #6C5CE7; font-weight: 700; }

/* Home button: larger, sits above the hero banner */
.st-key-home_btn button {
    font-size: 1.15rem;
    padding: 0.65rem 1.6rem;
    min-width: 180px;
}

/* Buttons */
.stButton > button {
    border-radius: 10px;
    border: none;
    font-weight: 600;
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(108, 92, 231, 0.35);
    filter: brightness(1.05);
}
.stButton > button:active { transform: translateY(0); }

/* Summary card (st.code block) */
[data-testid="stCodeBlock"] {
    border-radius: 12px;
    border: 1px solid #E6E8F2;
    box-shadow: 0 4px 14px rgba(31, 36, 48, 0.08);
    animation: cl-fade-in 0.5s ease-out;
}

/* Tables and charts */
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(31, 36, 48, 0.06);
}

/* Section headers */
h2, h3 { color: #2D3436; }
h2::after {
    content: "";
    display: block;
    width: 48px;
    height: 3px;
    margin-top: 0.3rem;
    border-radius: 3px;
    background: linear-gradient(90deg, #6C5CE7, #00CEC9);
}

/* Chat input: larger, bordered and shadowed so it stands out */
.st-key-chat_box [data-testid="stChatInput"] {
    border: 2px solid #6C5CE7;
    border-radius: 14px;
    box-shadow: 0 6px 18px rgba(108, 92, 231, 0.22);
    background: #FFFFFF;
    padding: 0.2rem 0.4rem;
}
.st-key-chat_box [data-testid="stChatInput"]:focus-within {
    border-color: #00CEC9;
    box-shadow: 0 0 0 4px rgba(0, 206, 201, 0.25);
}
.st-key-chat_box [data-testid="stChatInput"] textarea {
    font-size: 1.1rem;
    min-height: 3.2rem;
}
.cl-chat-intro {
    background: #F5F4FF;
    border-left: 5px solid #00CEC9;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.6rem;
    color: #2D3436;
}
.cl-chat-intro ul { margin: 0.3rem 0 0 1.1rem; padding: 0; }

/* Chat panel */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    background: #FFFFFF;
    border: 1px solid #E6E8F2;
    box-shadow: 0 2px 6px rgba(31, 36, 48, 0.05);
    animation: cl-fade-in 0.4s ease-out;
}

/* Expanders */
[data-testid="stExpander"] {
    border-radius: 12px;
    border: 1px solid #E6E8F2;
}

@keyframes cl-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""


def inject_css() -> None:
    """Visual styling only. No data or routing changes."""
    st.markdown(APP_CSS, unsafe_allow_html=True)


CLEAR_KEYS = ["case_id_input", "type_input", "subtype_input"]


def clear_search() -> None:
    for key in CLEAR_KEYS:
        st.session_state[key] = "" if key == "case_id_input" else "(any)"
    st.session_state.pop("pick_case", None)


def pick_case_id(df) -> str | None:
    """Show matching cases as a list. The user selects one to view its details and summary."""
    case_id = st.session_state.get("case_id_input", "").strip()
    if case_id:
        subset = df[df["Case_ID"] == case_id]
        if subset.empty:
            st.error(f"Case ID {case_id} not found.")
            return None
    else:
        type_val = st.session_state.get("type_input", "(any)")
        sub_val = st.session_state.get("subtype_input", "(any)")
        if type_val == "(any)" and sub_val == "(any)":
            st.info("Enter a Case ID, or choose a type or sub-type.")
            return None
        subset = df
        if type_val != "(any)":
            subset = subset[subset["Specific_Type"] == type_val]
        if sub_val != "(any)":
            subset = subset[subset["Specific_Sub_Type"] == sub_val]
        if subset.empty:
            st.error("No case matches these criteria.")
            return None

    st.subheader(f"{len(subset)} matching case(s)")
    st.dataframe(
        subset[["Case_ID", "Specific_Type", "Specific_Sub_Type"]].rename(
            columns={"Case_ID": "Case ID", "Specific_Type": "Type", "Specific_Sub_Type": "Sub-type"}
        ),
        hide_index=True,
    )
    return st.selectbox(
        "Select a case to view its summary",
        subset["Case_ID"].tolist(),
        index=None,
        placeholder="Choose a case",
        key="pick_case",
    )


def search_form(df) -> None:
    st.text_input("Case ID", key="case_id_input", placeholder="e.g. CS-2026-1001")
    has_case_id = bool(st.session_state.get("case_id_input", "").strip())
    type_val = st.session_state.get("type_input", "(any)")
    sub_val = st.session_state.get("subtype_input", "(any)")
    has_subtype = sub_val != "(any)"

    types = ["(any)"] + sorted(df["Specific_Type"].unique())
    subtype_pool = df if type_val == "(any)" else df[df["Specific_Type"] == type_val]
    subtypes = ["(any)"] + sorted(subtype_pool["Specific_Sub_Type"].unique())

    c1, c2 = st.columns(2)
    # A Case ID disables both dropdowns. A chosen sub-type disables the type dropdown.
    c1.selectbox("Type", types, key="type_input", disabled=has_case_id or has_subtype)
    c2.selectbox("Sub-type", subtypes, key="subtype_input", disabled=has_case_id)
    st.button("Clear search criteria", on_click=clear_search)


def single_case_page(df, patterns) -> None:
    st.header("Single case summarization")
    search_form(df)
    case_id = pick_case_id(df)
    if not case_id:
        return
    use_llm = st.checkbox("Use live model (uses OpenRouter credit)", value=False)

    facts = summary.case_facts(df, case_id, patterns)
    c1, c2, c3 = st.columns(3)
    c1.metric("Type", facts["type"])
    c2.metric("Sub-type", facts["sub_type"])
    c3.metric("Total TAT (h)", "Open" if pd.isna(facts["tat_hours"]) else f"{facts['tat_hours']:.1f}")
    st.caption(f"Status: {summary.status_text(facts)} | Documents attached: {facts['documents']}")

    result = summary.summarize_case(case_id, df=df, patterns=patterns, use_llm=use_llm)
    st.caption(f"Mode: {result['mode']}" + (f" ({result['model']})" if result["model"] else ""))
    if result["error"]:
        st.warning(f"Fell back to template: {result['error']}")
    card_text = summary.render_card(facts, result["lines"])
    st.code(card_text, language=None, wrap_lines=True)
    st.download_button("Download case card (PDF)", data=export_extra.card_pdf(card_text, f"Case {case_id}"),
                       file_name=f"{case_id}_card.pdf", mime=export_extra.PDF_MIME, key="dl_card")

    with st.expander("Stage comments (source data)"):
        rows = [
            {"Stage": n, "Name": summary.STAGE_NAMES[n], "Comment": facts["comments"][n]}
            for n in range(1, STAGES + 1)
        ]
        st.table(pd.DataFrame(rows))

    st.subheader("Jargon explained")
    if facts["terms"]:
        st.table(pd.DataFrame([
            {
                "ID": t["ID"],
                "Term": t["Term"],
                # Show the full form only when it adds information beyond the Term.
                "Full form": t["Full_Form"] if t["Full_Form"] != t["Term"] else "—",
                "Meaning": t["Plain_English_Explanation"],
            }
            for t in facts["terms"]
        ]))
    else:
        st.write("No dictionary terms in this case.")

    st.caption("Decision support only. A human makes the final decision.")


def date_filter(df):
    """Two date inputs (From, To) inside a form. The range applies only when the user submits.
    Returns the cases created in the applied range, or None if there is nothing to show."""
    created = df["Stage_1_Timestamp"].dropna()
    if created.empty:
        st.info("No case creation dates are available.")
        return None
    lo, hi = created.min().date(), created.max().date()

    with st.form("created_range_form", border=True):
        st.markdown("**Filter cases by creation date**")
        c1, c2, c3 = st.columns([1, 1, 0.6], vertical_alignment="bottom")
        start = c1.date_input("From", value=lo, min_value=lo, max_value=hi, format="DD/MM/YYYY")
        end = c2.date_input("To", value=hi, min_value=lo, max_value=hi, format="DD/MM/YYYY")
        submitted = c3.form_submit_button("Apply", type="primary", use_container_width=True)

    if submitted:
        if start > end:
            st.session_state["created_range"] = None
            st.error("The From date is after the To date. Pick a valid range and press Apply.")
        else:
            st.session_state["created_range"] = (start, end)

    applied = st.session_state.get("created_range") or (lo, hi)
    start, end = applied
    mask = (df["Stage_1_Timestamp"].dt.date >= start) & (df["Stage_1_Timestamp"].dt.date <= end)
    subset = df[mask].reset_index(drop=True)
    if subset.empty:
        st.warning(f"No cases were created between {start:%d %b %Y} and {end:%d %b %Y}.")
        return None
    st.success(
        f"**{len(subset)} case(s)** were created between {start:%d %b %Y} and {end:%d %b %Y}."
    )
    return subset


def filter_panel(df):
    """Combined filters inside a form. Results change only when Apply is pressed."""
    with st.expander("Filters", expanded=False):
        with st.form("filter_form", border=False):
            f1, f2, f3 = st.columns(3)
            types = sorted(df["Specific_Type"].unique())
            f1.multiselect("Type", types, key="flt_type")
            subs = sorted(df["Specific_Sub_Type"].unique())
            f2.multiselect("Sub-type", subs, key="flt_sub")
            f3.multiselect("Priority", ["P1", "P2"], key="flt_priority")
            g1, g2, g3 = st.columns(3)
            g1.selectbox("Status", ["Any", "Open", "Closed"], key="flt_status")
            g2.selectbox("Current stage", ["Any", 1, 2, 3, 4, 5], key="flt_stage")
            g3.selectbox("Documents", ["Any", "Yes", "No"], key="flt_docs")
            st.checkbox("Stalled cases only", key="flt_stalled")
            submitted = st.form_submit_button("Apply filters", type="primary")
    if submitted:
        _apply_filters_from_widgets()

    sel_type = st.session_state.get("applied_flt_type") or []
    sel_sub = st.session_state.get("applied_flt_sub") or []
    priority = st.session_state.get("applied_flt_priority") or []
    status = st.session_state.get("applied_flt_status") or "Any"
    stage = st.session_state.get("applied_flt_stage") or "Any"
    docs = st.session_state.get("applied_flt_docs") or "Any"
    stalled = bool(st.session_state.get("applied_flt_stalled"))

    mask = pd.Series(True, index=df.index)
    if sel_type:
        mask &= df["Specific_Type"].isin(sel_type)
    if sel_sub:
        mask &= df["Specific_Sub_Type"].isin(sel_sub)
    if priority and "Priority" in df.columns:
        mask &= df["Priority"].isin(priority)
    closed = sla.closed_flags(df)
    if status == "Open":
        mask &= ~closed
    elif status == "Closed":
        mask &= closed
    if docs != "Any":
        mask &= df["Documents_Attached"] == docs
    if stage != "Any":
        cur = pd.Series([summary_stage(df, i) for i in df.index], index=df.index)
        mask &= cur == int(stage)
    if stalled:
        mask &= pd.Series([len(summary.stall_stages(summary_comments(df, i), closed=bool(closed[i]))) > 0
                           for i in df.index],
                          index=df.index)
    return df[mask].reset_index(drop=True)


FILTER_KEYS = ["flt_type", "flt_sub", "flt_priority", "flt_status", "flt_stage", "flt_docs", "flt_stalled"]


def _apply_filters_from_widgets() -> None:
    """Copy the form widget values into the applied values the page reads."""
    for key in FILTER_KEYS:
        st.session_state["applied_" + key] = st.session_state.get(key)


def summary_stage(df, idx) -> int:
    """Latest stage with a non-blank comment, for the Current stage filter."""
    comments = summary_comments(df, idx)
    filled = [n for n in range(1, 6) if comments[n].strip()]
    return max(filled) if filled else 1


def summary_comments(df, idx) -> dict:
    row = df.loc[idx]
    return {n: row[f"Stage_{n}_Comments"] if isinstance(row[f"Stage_{n}_Comments"], str) else ""
            for n in range(1, 6)}


def sla_section(df, as_of=None) -> None:
    """Cases past their SLA: closed cases over target, and open cases already past target."""
    st.subheader("SLA breaches")
    breaches = sla.breach_table(df, as_of=as_of)
    if breaches.empty:
        st.success("No cases are past their SLA in this selection.")
        return
    closed_n = int((breaches["Status"] == "Closed").sum())
    st.caption(f"{len(breaches)} case(s) past SLA: {closed_n} closed late, {len(breaches) - closed_n} open and past target.")
    st.dataframe(breaches, hide_index=True)
    st.download_button("Download SLA breaches (CSV)", data=export_extra.table_csv(breaches),
                       file_name="caselens_sla_breaches.csv", mime=export_extra.CSV_MIME, key="dl_sla")


def batch_page(df, patterns) -> None:
    st.header("Batch view")
    all_df = df
    df = date_filter(df)
    if df is None:
        return
    lo, hi = all_df["Stage_1_Timestamp"].min().date(), all_df["Stage_1_Timestamp"].max().date()
    start, end = st.session_state.get("created_range") or (lo, hi)
    df = filter_panel(df)
    if df.empty:
        st.warning("No cases match the selected filters.")
        return
    total = total_tat_hours(df)
    stalls = [summary.case_facts(df, cid, patterns)["stalls"] for cid in df["Case_ID"]]
    summary_df = pd.DataFrame({
        "Case_ID": df["Case_ID"],
        "Created": df["Stage_1_Timestamp"].dt.strftime("%d-%b-%Y"),
        "Type": df["Specific_Type"],
        "Sub_type": df["Specific_Sub_Type"],
        "TAT_hours": total,
        "Stalled": [len(s) > 0 for s in stalls],
        "Closed": [summary.closed_status(row, row["Stage_5_Comments"]) for _, row in df.iterrows()],
    })

    c1, c2, c3 = st.columns(3)
    c1.metric("Cases", len(df))
    c2.metric("Stalled cases", int(summary_df["Stalled"].sum()))
    c3.metric("Average TAT (h)", f"{summary_df['TAT_hours'].mean():.1f}")

    by_type = summary_df.groupby("Type").agg(
        Cases=("Case_ID", "count"),
        Stalled=("Stalled", "sum"),
        Avg_TAT_hours=("TAT_hours", "mean"),
    ).reset_index()
    by_type["Stalled_%"] = (by_type["Stalled"] / by_type["Cases"] * 100).round(1)
    by_type["Avg_TAT_hours"] = by_type["Avg_TAT_hours"].round(1)

    bn = bottleneck_per_case(df)
    counts = bn.groupby("Stage").size().rename("Cases").reset_index()
    counts["Stage_name"] = counts["Stage"].map(summary.STAGE_NAMES)
    counts["Stage_label"] = counts["Stage"].map(lambda n: f"S{n} {summary.STAGE_NAMES[n]}")

    sub = summary_df.groupby("Sub_type").agg(
        Cases=("Case_ID", "count"), Stalled=("Stalled", "sum")
    ).reset_index()
    sub["Stalled_%"] = (sub["Stalled"] / sub["Cases"] * 100).round(1)

    st.subheader("Trend report")
    figs = trends.compute_figures(df, patterns)
    lines, mode = trends.narrative(figs)
    st.caption(f"Narrative: {mode}. Every figure is computed from the CSV.")
    for line in lines:
        st.write("- " + line)

    st.subheader("Charts")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Cases by type**")
        st.bar_chart(by_type.set_index("Type")[["Cases", "Stalled"]])
    with g2:
        st.markdown("**Average turnaround (hours) by type**")
        st.bar_chart(by_type.set_index("Type")[["Avg_TAT_hours"]])
    g3, g4 = st.columns(2)
    with g3:
        st.markdown("**Longest stage per case**")
        st.bar_chart(counts.set_index("Stage_label")[["Cases"]])
    with g4:
        st.markdown("**Stalled cases (%) by sub-type**")
        st.bar_chart(sub.set_index("Sub_type")[["Stalled_%"]])

    st.subheader("By type")
    st.dataframe(by_type, hide_index=True)

    st.subheader("Longest stage per case")
    st.dataframe(counts[["Stage", "Stage_name", "Cases"]], hide_index=True)

    st.subheader("Cases")
    st.dataframe(summary_df.round(1), hide_index=True)
    st.download_button("Download case list (CSV)", data=export_extra.table_csv(summary_df.round(1)),
                       file_name="caselens_cases.csv", mime=export_extra.CSV_MIME, key="dl_cases")

    sla_section(df)

    st.subheader("Export")
    report_rows = [
        ("Date range", f"{start:%d %b %Y} to {end:%d %b %Y}"),
        ("Cases", str(len(df))),
        ("Stalled cases", str(int(summary_df["Stalled"].sum()))),
        ("Average TAT (h)", f"{summary_df['TAT_hours'].mean():.1f}"),
        ("Narrative", mode),
    ] + [("Trend report", line) for line in lines]
    st.download_button(
        "Download Excel report",
        data=export.build_workbook(report_rows, by_type, counts, sub, summary_df.round(1)),
        file_name=f"caselens_bulk_{start:%Y%m%d}_{end:%Y%m%d}.xlsx",
        mime=export.MIME,
        type="primary",
    )


def feedback_buttons(index: int) -> None:
    """Thumbs up or down under an answer. A vote is logged once, as a feedback event, with no question text."""
    voted = st.session_state.setdefault("votes", {})
    if index in voted:
        st.caption(f"Thanks. You marked this answer {'helpful' if voted[index] == 'up' else 'not helpful'}.")
        return
    c1, c2, _ = st.columns([1, 1, 6])
    if c1.button("👍", key=f"up_{index}", help="Helpful"):
        voted[index] = "up"
        guardrails.audit("feedback", error="up")
        st.rerun()
    if c2.button("👎", key=f"down_{index}", help="Not helpful"):
        voted[index] = "down"
        guardrails.audit("feedback", error="down")
        st.rerun()


def chat_panel(df, patterns) -> None:
    """Chat on the landing page. History lasts for the browser session or until cleared.
    Each card is rendered once and stored, so reruns do not call the model again."""
    st.subheader("Ask CaseLens")
    st.markdown(
        '<div class="cl-chat-intro"><strong>Try asking:</strong><ul>'
        "<li>summary of CS-2026-1001</li>"
        "<li>what is LTV?</li>"
        "<li>which case took the longest?</li>"
        "<li>why is CS-2026-1001 stalled?</li>"
        "<li>what documents are needed for a personal loan?</li>"
        "</ul></div>",
        unsafe_allow_html=True,
    )
    history = st.session_state.setdefault("chat", [])

    if st.button("Clear chat"):
        st.session_state["chat"] = []
        st.rerun()

    box = st.container(height=440, key="chat_box")
    with box:
        for msg in history:
            with st.chat_message(msg["role"]):
                for card in msg.get("cards", []):
                    st.code(card, language=None, wrap_lines=True)
                if msg.get("content"):
                    # Code block gives a built-in copy button. Markdown is shown as plain text.
                    if msg["role"] == "assistant":
                        st.code(msg["content"], language=None, wrap_lines=True)
                    else:
                        st.markdown(msg["content"])
                if msg["role"] == "assistant" and (msg.get("content") or msg.get("cards")):
                    feedback_buttons(history.index(msg))

    question = box.chat_input("Ask about a case or a jargon term")
    if not question:
        return

    # Show the question at once, then wait for the answer with a spinner.
    with box.chat_message("user"):
        st.markdown(question)
    with box.chat_message("assistant"):
        with st.spinner("Thinking... preparing the answer"):
            reply = chat.answer(question, df, patterns, get_entries(), history=history)
            cards = []
            if reply["kind"] == "cases":
                for cid in reply["case_ids"]:
                    facts = summary.case_facts(df, cid, patterns)
                    result = summary.summarize_case(cid, df=df, patterns=patterns, use_llm=True)
                    cards.append(guardrails.redact_output(summary.render_card(facts, result["lines"])))
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": reply["text"], "cards": cards,
                    "case_ids": reply.get("case_ids", [])})
    st.rerun()


def audit_page() -> None:
    """Audit view: every logged event, with latency and tokens. Read-only, from logs/audit.jsonl."""
    st.header("Audit view")
    st.caption("Every model call and guardrail event is logged here. Raw questions and keys are never stored.")
    log = audit_view.load_log()
    if log.empty:
        st.info("No audit events yet. Ask a question in the chat or run a summary to create events.")
        return

    head = audit_view.summary(log)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Events", head["events"])
    c2.metric("Model calls", head["model_calls"])
    c3.metric("Avg latency (ms)", "n/a" if head["avg_latency_ms"] is None else f"{head['avg_latency_ms']:.0f}")
    c4.metric("Total tokens", "n/a" if head["total_tokens"] is None else f"{head['total_tokens']:,}")
    price = summary.get_price_per_1k()
    model_rows = audit_view.model_events(log)
    per_call = audit_view.cost_per_call(model_rows, price).dropna()
    if price <= 0:
        st.caption("Cost: set OPENROUTER_PRICE_PER_1K_TOKENS in .env to show cost per call and per summary.")
    elif per_call.empty:
        st.caption("Cost: no token counts logged yet.")
    else:
        cc1, cc2 = st.columns(2)
        cc1.metric("Cost per model call (USD)", f"${per_call.mean():.4f}")
        cc2.metric("Total estimated cost (USD)", f"${per_call.sum():.2f}")
        st.subheader("Cost by summary")
        st.caption("Each row is one summary card. Its cost is the sum of every model call tagged with its summary ID.")
        st.dataframe(audit_view.cost_by_summary(log, price), hide_index=True)
        st.subheader("Cost by case")
        st.dataframe(audit_view.cost_by_case(log, price), hide_index=True)
    h1, h2 = st.columns(2)
    h1.metric("Summary cache hits", head["cache_hits"],
              help="Summaries served from cache. No model call was made for these.")
    h2.metric("Tokens saved (est.)",
              "n/a" if head["tokens_saved"] is None else f"{head['tokens_saved']:,}",
              help="Each cache hit is estimated at the average tokens of a logged summary call.")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("p95 latency (ms)", "n/a" if head["p95_latency_ms"] is None else f"{head['p95_latency_ms']:.0f}")
    c6.metric("Avg tokens per call", "n/a" if head["avg_tokens_per_call"] is None else f"{head['avg_tokens_per_call']:.0f}")
    c7.metric("Real errors", head["errors"], help="Model or system failures. Guardrail blocks are counted separately.")
    c8.metric("Guardrail blocks", head["blocked"], help="Questions stopped before a model call, for example PII requests.")
    st.caption(f"Lines dropped by the citation check: {head['dropped_lines']}.")

    st.subheader("By event type")
    st.dataframe(audit_view.by_kind(log), hide_index=True)

    st.subheader("Prompt version comparison")
    st.caption("Latency, tokens, and dropped lines per prompt version. Use this to compare prompt changes.")
    st.dataframe(audit_view.by_prompt_version(log), hide_index=True)

    st.subheader("Human feedback")
    fb = audit_view.feedback_summary(log)
    if fb["total"] == 0:
        st.info("No feedback yet. Thumbs up or down under a chat answer to record it.")
    else:
        share = "n/a" if fb["helpful_share"] is None else f"{fb['helpful_share']:.0%}"
        f1, f2, f3 = st.columns(3)
        f1.metric("Helpful (👍)", fb["up"])
        f2.metric("Not helpful (👎)", fb["down"])
        f3.metric("Helpful share", share)

    st.subheader("Events")
    kinds = sorted(k for k in log["kind"].dropna().unique())
    models = sorted(m for m in log["model"].dropna().unique() if m)
    f1, f2 = st.columns(2)
    sel_kind = f1.multiselect("Event type", kinds, key="audit_kind")
    sel_model = f2.multiselect("Model", models, key="audit_model")
    filtered = audit_view.filter_log(log, kinds=sel_kind, models=sel_model)
    st.caption(f"{len(filtered)} event(s) shown. Blank latency or tokens mean no model call was made.")
    st.dataframe(filtered, hide_index=True)
    st.download_button("Download audit events (CSV)", data=export_extra.table_csv(filtered),
                       file_name="caselens_audit.csv", mime=export_extra.CSV_MIME, key="dl_audit")


def _audit_log_key() -> str:
    """Changes whenever the audit log changes, so the cached scorecard is refreshed after new events."""
    path = guardrails.LOG_PATH
    if not path.exists():
        return "no-log"
    stat = path.stat()
    return f"{stat.st_mtime_ns}-{stat.st_size}"


@st.cache_data(show_spinner=False)
def _scorecard_board(log_key: str, _df, _patterns, _entries):
    """Runs the scorecard checks. Cached by log_key; the underscored arguments are not hashed."""
    return scorecard.build(_df, _patterns, audit_view.load_log(), _entries)


def scorecard_page(df, patterns) -> None:
    """Evaluation scorecard. The checks run only on request and are cached until the audit log changes."""
    st.header("Evaluation scorecard")
    st.caption("Measured on the current data. Template checks run offline. Latency and tokens come from the audit log.")
    if st.button("Run scorecard", type="primary"):
        st.session_state["scorecard_requested"] = True
    if not st.session_state.get("scorecard_requested"):
        st.info("Press Run scorecard. The checks ask the chat 30 invented-term questions and summarise all 500 cases, "
                "so the first run takes a few minutes. The result is kept until the audit log changes.")
        return
    with st.spinner("Running checks..."):
        board = _scorecard_board(_audit_log_key(), df, patterns, get_entries())
    st.dataframe(board, hide_index=True)
    st.caption("A target marked 'not measured' has no data yet, so it is not a pass.")


def nav_bar() -> None:
    """Home, Audit view, and Evaluation scorecard in one row. Each sets the page mode on the same page."""
    c1, c2, c3 = st.columns(3)
    if c1.button("🏠 Home", use_container_width=True, type="primary", key="nav_home"):
        st.session_state["mode"] = None
        st.rerun()
    if c2.button("🧾 Audit view", use_container_width=True, type="primary", key="nav_audit"):
        st.session_state["mode"] = "audit"
        st.rerun()
    if c3.button("✅ Evaluation scorecard", use_container_width=True, type="primary", key="nav_scorecard"):
        st.session_state["mode"] = "scorecard"
        st.rerun()


def landing(df, patterns) -> None:
    st.header("Choose an option")
    st.caption("Pick a view to start. Cases and jargon are read from the CSV and dictionary.")
    c1, c2 = st.columns(2)
    if c1.button("🔍 Single Case Summarization", use_container_width=True, type="primary"):
        st.session_state["mode"] = "single"
        st.rerun()
    if c2.button("📊 Bulk Case Summarization", use_container_width=True, type="primary"):
        st.session_state["mode"] = "bulk"
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="CaseLens", layout="wide", initial_sidebar_state="collapsed")
    inject_css()
    df = get_cases()
    patterns = get_patterns()
    mode = st.session_state.get("mode")

    if mode in ("audit", "scorecard"):
        # Full-width views: same page, no chat.
        st.markdown('<div class="cl-hero"><h1>CaseLens</h1>'
                    "<p>Ask questions about BPM cases and business terms, in plain English</p></div>",
                    unsafe_allow_html=True)
        nav_bar()
        if mode == "audit":
            audit_page()
        else:
            scorecard_page(df, patterns)
        return

    left, right = st.columns([2, 1.3], gap="medium")
    with left:
        st.markdown(
            '<div class="cl-hero"><h1>CaseLens</h1>'
            "<p>Ask questions about BPM cases and business terms, in plain English</p></div>",
            unsafe_allow_html=True,
        )
        nav_bar()
        if mode == "single":
            if st.button("⬅ Back", type="primary"):
                st.session_state["mode"] = None
                st.rerun()
            single_case_page(df, patterns)
        elif mode == "bulk":
            if st.button("⬅ Back", type="primary"):
                st.session_state["mode"] = None
                st.rerun()
            batch_page(df, patterns)
        else:
            landing(df, patterns)
    with right:
        chat_panel(df, patterns)


if __name__ == "__main__":
    main()
