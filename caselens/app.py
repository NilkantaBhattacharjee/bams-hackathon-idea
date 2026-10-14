"""CaseLens Streamlit app: single-case summary and batch view."""

import pandas as pd
import streamlit as st

import chat
import guardrails
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
    st.code(summary.render_card(facts, result["lines"]), language=None, wrap_lines=True)

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


def batch_page(df, patterns) -> None:
    st.header("Batch view")
    total = total_tat_hours(df)
    stalls = [summary.case_facts(df, cid, patterns)["stalls"] for cid in df["Case_ID"]]
    summary_df = pd.DataFrame({
        "Case_ID": df["Case_ID"],
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


def chat_panel(df, patterns) -> None:
    """Chat on the landing page. History lasts for the browser session or until cleared.
    Each card is rendered once and stored, so reruns do not call the model again."""
    st.subheader("Ask CaseLens")
    st.caption("e.g. 'summary of CS-2026-1001' or 'what is LTV?'")
    history = st.session_state.setdefault("chat", [])

    if st.button("Clear chat"):
        st.session_state["chat"] = []
        st.rerun()

    box = st.container(height=440)
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

    left, right = st.columns([2, 1.3], gap="medium")
    with left:
        if mode:
            with st.container(key="home_btn"):
                if st.button("⬅ Home", type="primary"):
                    st.session_state["mode"] = None
                    st.rerun()
        st.markdown(
            '<div class="cl-hero"><h1>CaseLens</h1>'
            "<p>Plain-English case intelligence for BPM operations</p></div>",
            unsafe_allow_html=True,
        )
        if mode == "single":
            single_case_page(df, patterns)
        elif mode == "bulk":
            batch_page(df, patterns)
        else:
            landing(df, patterns)
    with right:
        chat_panel(df, patterns)


if __name__ == "__main__":
    main()
