# CaseLens: Idea Submission

## Idea Title

**CaseLens: Grounded Case Intelligence for Banking/Financial Operations**

---

## Problem Statement

In banking/financial operations, every business process management (BPM) case carries a long trail of comments across different stages. The comments are written in shorthand: KYC, PEP, LTV, DTI, CBS, STP, and many more.

The responsible associates have to read those comments to answer three questions: what is the status of this case, why is it open or stalled, and what happens next. Managers ask for trends over a period, such as how many cases are still open or stalled and how long they take. Auditors need to review a set of cases through trends and charts.

Reviewing mutiple cases manually might take considerably longer time. The answers are spread across several screens, and nothing gives a quick trend view for a chosen period.

---

## Idea Description

CaseLens is a working assistant that turns raw case records into short, plain-English answers. It does three things.

1. **One-step case summary.** A person enters a case ID, or asks "summary of CS-2026-1001". The answer is a single card with status, stage timeline, documents, SLA target, and each abbreviation explained in plain words.
2. **Trend report for any period.** A person picks a date range, such as the last one or two months. The view shows how many cases are open, stalled, or closed, and the average turnaround, with charts.
3. **Auditor review by trend and chart.** An auditor reviews a set of cases through charts and an exportable workbook, and the tool logs how it was used.

The idea is that the system provides an interactive chat functionality for the user to get summary or any details pertaining to any individual case. The glossary and financial terms are matched by phrase and, for close wording, by a local embedding search. The matched entries are the only source the model may cite, which is a retrieval-augmented (RAG) approach.

Every figure is computed from the case data. The model is used to write a sentence about a fact that code has already computed, and every line it writes must cite its source. A line without a valid source is removed and counted. An abbreviation that is not in the dictionary is reported as "not in the glossary", not guessed.

A human makes every decision. CaseLens gives a summary and its sources. Users can mark each answer helpful or not.

---

## Benefits & Impacts

**For the financial associates**
- Case work in BPM is adaptive, not fixed-sequence, and requires gathering information, reviewing documents, clarifying decisions, and understanding context.- A case summary takes one step instead of going through several screens, gathering information, and understanding the case to take an action.
- Abbreviations are explained in place, so less time is spent looking them up.

**For managers**
- Open, stalled, and closed counts and the average turnaround for any chosen period, in one view, without building a report manually.

**For auditors and risk teams**
- Trends and charts across a set of cases, with an export, instead of reading each case.
- An audit log of every model call, guardrail block, and feedback vote, which records counts and hashes but never raw questions or keys.

**For the financial institution**
- Lower risk of wrong answers: every number is computed, every model line is checked against its source, and invented terms are refused. On our test set, 100% of summary lines cite a source, and 30 of 30 invented terms are refused.
- Low running cost: about $0.0005 per summary at the estimated model price.
- Client data is masked before any model call, and personal-data questions are refused.

**Scale of the problem**
- The prototype uses 500 synthetic cases in a CSV file. The same approach applies to any BPM case set with stage timestamps and comments. In production, case data would come from the BPM database through an API. The glossary is small in the prototype, and a production glossary would be larger, possibly built from company documents. Those documents would need to be embedded and stored in a vector store, which is planned but not built yet as part of this prototype.

---

## Solution (Architecture, Tools, Infrastructure, Data, etc.)

**Architecture**
- A Streamlit web app (`app.py`) with a case page, a bulk trend page, a chat panel, an audit page, and an evaluation scorecard.
- A rule-based question router (`chat.py`) that decides how each question is answered: a case card, a glossary entry, a computed figure, or a refusal.
- A deterministic metrics layer (`metrics.py`, `trends.py`, `sla.py`) that computes stage durations, turnaround, stall flags, and SLA breaches with pandas. The model does no arithmetic.
- A glossary layer (`jargon.py`, `semantic.py`) that matches abbreviations by whole phrase and uses a local sentence-embedding model for close matches.
- A guardrails layer (`guardrails.py`, `chat.py`) that checks input, masks client details before any model call, and redacts the output.
- A citation check (`summary.py`, `keep_cited`) that keeps only model lines with a valid source.
- A summary cache, which serves repeat summaries for an unchanged case without a model call.
- An audit log and an audit view (`audit_view.py`) that show model calls, cost per summary, cache hits, prompt-version comparison, and feedback.
- An evaluation scorecard (`scorecard.py`) and a live evaluation script (`eval/run_live_eval.py`).

**Tools and models**
- Python, pandas, Streamlit (UI), openpyxl (Excel export), reportlab (PDF export).
- Model: `openai/gpt-4o-mini` through OpenRouter's chat API, at temperature 0.
- Local embeddings: `all-MiniLM-L6-v2`, run on the user's machine (as this is a prototype).

**Infrastructure**
- The prototype runs locally with one command: `py -m streamlit run app.py`.
- A production deployment would host the app behind the bank's network, store the API key in a managed secret store, and move the audit log to a managed store. These are not built as part of this prototype.

**Data**
- Case records: a CSV of case IDs, types, stage timestamps and comments, turnaround, documents, and SLA targets. 500 synthetic cases; no real customer data.
- Glossary: a JSON dictionary of 52 banking terms with plain-English explanations.
- Every name, account number, email, and phone number is synthetic.

**Controls and testing**
- 150 automated tests, all passing in the latest full run.
- A scorecard with four measured targets: grounding 100%, invented terms refused 30 of 30, raw client IDs in output 0, p95 latency 2.5 seconds.
- A live evaluation on the real model: summaries 10 of 10, chat 9 of 9, trend narrative passed.
- A risk register with nine risks, a compliance note, and a list of known failures.

---

## Any additional info

**Current status.** A working prototype. Browser checks of the main pages passed.

**Limits, stated openly.**
- All data is synthetic. A real deployment needs a data-protection review first.
- The system is grounded and rule-routed, not an autonomous agent. The model does not choose tools or take actions.
- Retrieval quality is measured only on 30 invented terms, not on real staff questions.
- Citations are checked and logged but not shown on the case card.


**Supporting documents** (in the project's `docs/deliverables` folder): problem statement, risk register, cost estimate, monitoring plan, architecture diagram, technical write-up, and presentation script.
