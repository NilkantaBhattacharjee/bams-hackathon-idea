# CaseLens: Chat History and Decisions

Summary of the working session. The raw transcript is not stored in this repo because it contains a secret that was pasted into the chat.

## 1. Goal

Build a BPM case copilot ("CaseLens") for a hackathon. It should show agentic AI, GenAI, RAG, business value and architecture quality, with masking, guardrails and prompt-injection defence.

Requirements raised by the user:
- View a summary of each case.
- Validate the idea and judge whether a prototype is quick to build.
- Refine requirements so the jury will accept them.
- A chatbot that answers questions about cases and jargon. It keeps context until the window closes or the user clears the chat.
- Landing page with no pre-populated dropdown. Two options: Single Case Summarisation and Bulk Case Summarisation.
- Single-case search by Case ID, with Type and Sub-type rules and a clear option.
- Explain how to check the install, whether RAG/embeddings are used, and how to test and log guardrails and security.

## 2. Decisions

- **Stack:** Python with Streamlit. Data is pandas; tests use pytest.
- **LLM:** OpenRouter, model `openai/gpt-4o-mini`. The key is read from `caselens/.env`. Rotate it, because it was shared in chat.
- **Embeddings:** `all-MiniLM-L6-v2` run locally with sentence-transformers, in memory. Only the jargon glossary is embedded. Case records are not embedded yet.
- **Architecture:** deterministic metrics, then routing rules, then optional semantic glossary lookup, then a masked prompt, then the LLM, then a citation check, then audit logging, then the Streamlit UI.
- **Stage model:** five stages. Stage durations are the gap to the next stage entry. Stage 5 has no exit. Closed status comes from the Stage 5 comment.
- **Data location:** the two source files now live in `caselens/syntheticData/`. The paths are set in `caselens/config.py`.

## 3. Data

- `Financial_BPM_Cases_100 - Untitled.csv`: 100 cases (CS-2026-1001 to CS-2026-1100), 4 types and 8 sub-types. `SLA_Days` and `Document_Details` were added synthetically.
- `financial_jargon_dictionary.json`: 52 entries (JD-001 to JD-052), with status confirmed or to_confirm.
- A backup of the CSV from before the field additions is still in `Idea/`.

## 4. Guardrails and security

| Control | Behaviour |
|---|---|
| Input length | Questions over 500 characters are refused. |
| Instruction override | Attack phrases are refused before any model call. |
| Client ID and email | Masked before the model call. A raw identifier blocks the call. |
| Untrusted input | User text is wrapped as data, and case comments are treated as data. |
| Citations | Lines without a valid source are dropped. Jargon citations also need a word overlap. |
| Audit log | One JSON line per chat turn in `logs/audit.jsonl`. It stores version, hash, route and citation counts. It never stores the raw question, IDs, emails or the key. |

## 5. Tests and evaluation

- `py -m pytest -q` from `caselens`: 96 tests, all passing.
- `eval/run_eval.py`: offline evaluation, 100% citation coverage and zero raw IDs.
- `eval/run_live_eval.py`: live evaluation. Summaries 9/10, chat 8/9, trend narrative passed. One case timed out and one fake term was marked for review.
- `eval/run_guardrail_demo.py`: 6/7 passing. The "email masked" check still fails inside the demo script, even though masking works and the unit test `test_pii_is_masked_before_model_call` passes.

## 6. Open items

1. Fix or remove the failing "email masked" demo check.
2. Check the running app in a browser. The last `streamlit run app.py` exited with code 1, so its error needs reviewing.
3. Re-run the live evaluation to address the CS-2026-1012 timeout and the fake-term review.
4. Update the architecture diagram: chat, case facts, semantic glossary, guardrails and audit, demo log, bulk dashboard.
5. Write a risk register and a monitoring note.
6. Rotate the OpenRouter key.
7. Push to GitHub. Git was not installed; the installer was cancelled. A `.gitignore` is in place.

## 7. Where things are

- App: `caselens/app.py`
- Chat: `caselens/chat.py`
- Guardrails: `caselens/guardrails.py`
- Semantic search: `caselens/semantic.py`
- Summaries: `caselens/summary.py`
- Config: `caselens/config.py`
- Tests: `caselens/tests/`
- Evaluations: `caselens/eval/`
