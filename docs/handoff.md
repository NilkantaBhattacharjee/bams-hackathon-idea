# CaseLens: Handoff for a New Session

Read this file first. It holds the full context of the project: what is being built, why, the data rules, the code that exists, what is working, what is broken, and what to do next. The session summary is in `docs/chat-history.md`. Secrets are deliberately excluded: the OpenRouter key lives only in `caselens/.env`, and it should be rotated.

---

## 1. The project

**Name:** CaseLens. A GenAI and agentic case-intelligence prototype for a banking BPM (business process management) system.

**Context:** a hackathon. The jury looks for Agentic AI, GenAI, RAG, business value, architecture quality, grounding, security and guardrails, responsible AI, LLMOps and evaluation, and cost and performance.

**The problem:** BPM cases in banking are hard to read quickly. Comments are full of abbreviations (KYC, PEP, LTV, DTI, CBS, STP, and others). Stage timestamps are scattered. Managers, auditors and shift staff spend time reconstructing what happened and why a case stalled.

**The solution:** an assistant that turns raw case data into grounded, plain-English summaries.
- Single case: a summary card, stage timeline, bottleneck, sources and jargon explanations.
- Bulk: trends across cases (counts by type and stage, bottlenecks, recurring issues).
- Chat: answers questions about cases and jargon, keeps context until the window closes or the user clears it.

**Principles the user set:**
- Facts come from code (pandas), not from the LLM. The LLM only explains computed facts.
- Jargon is explained only from the dictionary (RAG). Unknown terms are labelled "not in glossary", never guessed.
- Every claim cites a source: a case ID, a stage, or a dictionary ID (`JD-###`).
- PII is masked before any LLM call. Comments are treated as data, not instructions.
- Output is decision support only. A human decides.

---

## 2. Input data (the source of truth)

The user corrected earlier assumptions. **Work only from the files as they are.** Do not assume extra case types, stages or fields.

### 2.1 Case CSV

File: `caselens/syntheticData/Financial_BPM_Cases_100 - Untitled.csv`

Fields:
- `Case_ID` (CS-2026-1001 to CS-2026-1100, 100 rows)
- `Client_ID`
- `Specific_Type` (4 values): Retail_Banking, Commercial_Lending, Wealth_Management, Credit_Cards
- `Specific_Sub_Type` (8 values): Mortgage_Refinance, Personal_Loan, SME_Working_Capital, Equipment_Financing, Portfolio_Transfer, Estate_Account_Opening, Fraud_Dispute, Credit_Limit_Increase
- `Stage_1_Timestamp` to `Stage_5_Timestamp`, each with a `Stage_N_Comments`
- `Total_TAT_Hours`
- `Documents_Attached` (Yes or No)
- Added synthetically by `add_case_fields.py`: `SLA_Days` and `Document_Details`. A backup from before the addition is in `Idea/`.

Timestamp rule, confirmed against the data:
- `Stage_N_Timestamp` is the time the case **entered** stage N.
- Duration of stages 1 to 4 = next stage entry minus this stage entry.
- Stage 5 has only an entry time, so its duration and an end time cannot be computed.
- `Total_TAT_Hours` = Stage 5 entry minus Stage 1 entry. Example: CS-2026-1001 is 145.5 h, which matches.

Known data issue:
- CS-2026-1097: the Stage 2 timestamp (2026-03-03) is before Stage 1 (2026-04-02). Flag it; do not silently fix it.
- Other TAT mismatches were raised earlier, but they were checked under a different definition. Recheck all 100 rows with the rule above before counting them.

### 2.2 Jargon dictionary

File: `caselens/syntheticData/financial_jargon_dictionary.json`

Each entry has the fields `ID`, `Term`, `Category`, `Full_Form`, `Plain_English_Explanation`, `Status`.
- `ID` is `JD-001` to `JD-051` (51 entries). The file header in earlier notes said 52, so count the file again before relying on either number.
- `Status` is `confirmed` or `to_confirm`. Most new entries are `to_confirm` because the definitions are general industry meanings, not the bank's own.
- The JSON has **not** been validated with a parser since the last edits. Run a JSON check first.
- Pending: the terms SME (JD-050) and Wire Transfer (JD-051) were added last.
- Some comment terms were noted as not yet added: paystub (added as JD-040), notary (JD-041), death certificate (JD-042), e-signed (JD-043), Trust and Estate (JD-044). Confirm coverage by scanning every comment.
- Confusable pairs from the original brief (AML-KYC-EDD vs FCC-SAR, STP vs MRL): EDD, FCC, SAR and MRL do not appear in the case comments. Mark them as absent from the dataset if they are kept.

---

## 3. Requirements (refined)

### 3.1 Functional

- **FR1 Ingestion:** load the CSV with schema checks. Report bad rows (missing or out-of-order timestamps) instead of guessing.
- **FR2 Metrics:** compute stage durations, total TAT, bottleneck stage and SLA breach in pandas. Test with hand-checked cases.
- **FR3 Jargon:** find terms in comments, look them up in the dictionary, and cite the `JD-###` ID. Unknown terms: "not in glossary".
- **FR4 Single-case summary:** overview, current stage, timeline, stall cause, documents status, jargon explained, next action, and sources.
- **FR5 Bulk summary:** group by type and sub-type, then stage. Counts and percentages come from code. The LLM only writes the narrative.
- **FR6 Shift handover:** a fixed 3-bullet summary per case: current state, key history, next action.
- **FR7 Chat:** answers case and jargon questions. Keeps context until the window closes or the user clears it.
- **FR8 Guardrails:** refuse questions outside the case data; block prompt injection; mask PII before the model call.

### 3.2 Non-functional (what judges check)

- Grounding: share of summary sentences with a valid citation (target 95% or more).
- Accuracy: jargon explanations against a gold set.
- Hallucination: fake terms must return "not in glossary" (target 100%).
- Security: PII leak count in outgoing prompts = 0.
- Responsible AI: decision-support label, audit log, human in the loop.
- Cost: tokens and cost per summary, logged.
- Latency: a single case in a few seconds.
- LLMOps: prompt version tracked in the audit log; a monitoring note.

### 3.3 Deliverables for the hackathon

One-page problem statement (with a persona and numeric KPIs), architecture diagram, working demo, evaluation results, risk register and control notes, cost estimate, monitoring plan.

---

## 4. Decisions made

| Area | Decision |
|---|---|
| App | Python, Streamlit. React was cut for time. |
| LLM | OpenRouter. Dev model: `openai/gpt-4o-mini`. Demo option: a stronger model such as `openai/gpt-4o`. Model is set in `.env`. |
| Embeddings | `all-MiniLM-L6-v2`, run locally with sentence-transformers. Glossary only; case records are not embedded. |
| Vector store | In-memory cosine similarity. No FAISS. `MIN_SCORE` = 0.35. |
| Routing | Rules first (case facts, lists, status, jargon), then semantic glossary, then the LLM. |
| Stage model | Five stages. Closed status is read from the Stage 5 comment. |
| Data location | `caselens/syntheticData/`, set in `caselens/config.py` via `DATA_DIR`. |
| Git | Repo at `bpm-case-copilot/`. `.gitignore` covers `.env`, `__pycache__/`, `.pytest_cache/`, `.venv/`, `logs/`. |

---

## 5. Architecture

```
User (Streamlit)
  -> CSV ingestion + validation (metrics.py, validate.py)
  -> deterministic metrics (metrics.py, case_facts.py)
  -> routing (chat.py)
       -> case facts / list / status / jargon (rules)
       -> semantic glossary search (semantic.py)
  -> masking + guardrails (summary.py mask, guardrails.py)
  -> LLM via OpenRouter (summary.py call_llm, chat.py call_chat)
  -> citation check (summary.keep_cited)
  -> audit log (logs/audit.jsonl) + demo log (logs/demo.log)
  -> Streamlit UI (app.py)
```

Bulk trend narrative: `trends.py` (`compute_figures`, `figures_block`, `narrative`).

---

## 6. Code map (`caselens/`)

| File | Purpose |
|---|---|
| `config.py` | Paths (`DATA_DIR`, `CASES_CSV`, `JARGON_JSON`, reports) and TAT tolerance. |
| `metrics.py` | `load_cases`, `stage_durations`, `total_tat_hours`, `bottleneck_per_case`. |
| `validate.py` | Data checks; writes `reports/data_validation.md`. |
| `jargon.py` | Builds term patterns; `find_terms`, `explain_comments`, `load_entries`; writes `reports/jargon_lookup.md`. |
| `summary.py` | Case facts, `mask`, prompt building, template fallback, `call_llm`, `keep_cited`, `is_closed`, `stall_stages`, `render_card`, `summarize_case`. |
| `case_facts.py` | `answer_facts`, stage text and hours, documents text, `list_cases` (max 10). |
| `chat.py` | `answer()` entry point, routing, `llm_answer`, `call_chat`, refusal messages. |
| `guardrails.py` | `leaks`, `injection_hits`, `masked_ok`, `prompt_hash`, `audit()`; `PROMPT_VERSION = "chat-v2"`. |
| `demo_log.py` | Step logging to console and `logs/demo.log`. |
| `semantic.py` | Lazy model load, glossary embeddings, `search_glossary`. |
| `trends.py` | Bulk figures and narrative. |
| `app.py` | Streamlit app: landing, single case, bulk view with charts, chat panel. |
| `add_case_fields.py` | One-time script that added `SLA_Days` and `Document_Details` (done). |
| `tests/` | 96 pytest tests, all passing. |
| `eval/run_eval.py` | Offline evaluation. |
| `eval/run_live_eval.py` | Live evaluation; writes `eval/live_results.md`. |
| `eval/run_guardrail_demo.py` | 7 guardrail checks. |
| `requirements.txt` | pandas, pytest, tabulate, streamlit (sentence-transformers installed separately). |
| `.env` | `OPENROUTER_API_KEY` and model. Never commit. |
| `logs/` | `audit.jsonl`, `demo.log`. Never commit. |

---

## 7. Current status

**Working**
- 96 pytest tests pass (run from `caselens/`).
- Offline evaluation: 100% citation coverage, 0 raw IDs.
- Masking works: the raw email is absent from the prompt and `[EMAIL]` is present (verified directly).
- Guardrail refusals verified: instruction override, over-long input, raw client ID blocks the model call.
- Semantic glossary tests pass (5/5).
- Data moved to `caselens/syntheticData/`; tests pass with the new paths.
- Trend narrative passed in the last live run.

**Not working or unresolved**
1. **Guardrail demo: 6/7.** The "email masked" check fails inside `eval/run_guardrail_demo.py`, even though masking works. The same behaviour passes as the unit test `test_pii_is_masked_before_model_call`. The most recent demo run also showed "unknown term not invented" failing, so that check needs a look too. Fix the harness or rely on the unit tests, and say which in the demo.
2. **Streamlit app:** the last `py -m streamlit run app.py` exited with code 1. The error has not been captured. Run it again and read the traceback first.
3. **Live evaluation:** one case (CS-2026-1012) timed out, and one fake term was marked for review. Re-run `eval/run_live_eval.py`.
4. **Data:** CS-2026-1097 out-of-order timestamps. Recheck TAT mismatches under the confirmed rule.
5. **Dictionary:** not validated as JSON since the last edits. Check whether SME, Wire Transfer and the missing comment terms are complete.
6. **Security:** the OpenRouter key was pasted into the chat. Rotate it and update `caselens/.env`.
7. **Git:** Git is not installed (the installer was cancelled). Install Git, then `git init`, commit, create the GitHub repo, and push. The `.gitignore` is in place.
8. **Docs still to write:** updated architecture diagram, risk register, monitoring note, cost estimate, one-page problem statement with persona and KPIs.

---

## 8. Commands

Run from `C:\Users\nilkbhat\bpm-case-copilot\caselens`:

```powershell
py -m pytest -q                      # 96 tests
py -m streamlit run app.py           # app
py eval\run_eval.py                  # offline evaluation
py eval\run_live_eval.py             # live evaluation (needs API key)
py eval\run_guardrail_demo.py        # guardrail checks
py validate.py                       # data validation report (reports/data_validation.md)
Get-Content logs\audit.jsonl -Tail 5 # audit log
```

Python is run with the `py` launcher (Python 3.14.3). `python` is not on PATH.

---

## 9. Lessons and rules for the next session

- Use the CSV and the JSON as they are. Do not add assumed case types, stages or fields.
- Verify each file parses after an edit. Multiple partial edits broke files before; prefer full-function rewrites.
- Run pytest from `caselens/`, not the repo root.
- Keep tests on the public entry point (`chat.answer`), not private helpers.
- Never log raw questions, client IDs, emails or keys. The audit log stores hashes and IDs of the prompt version only.
- LLM output needs two checks: the citation ID must exist, and the cited content must overlap the source.
- Source data is read only. Issues go to a report, not into the CSV.

---

## 10. Suggested next steps

1. Rotate the key. Confirm `.env` is git-ignored.
2. Run the app and capture any traceback. Fix it.
3. Run `py -m pytest -q` and confirm 96 pass.
4. Validate the JSON dictionary and close the coverage gaps listed in section 2.2.
5. Fix or document the guardrail demo's failing checks.
6. Re-run the live evaluation and record real numbers.
7. Write the deliverables: architecture diagram, risk register, monitoring note, cost estimate, problem statement with persona and KPIs.
8. Install Git and push to GitHub.
