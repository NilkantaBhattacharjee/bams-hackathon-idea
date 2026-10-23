# CaseLens: Presentation Script (about 10 minutes)

## Before you start

- Start the app: `py -m streamlit run app.py` from the `caselens` folder.
- Open the Home page. Have these ready: `summary of CS-2026-1001`, `what is LTV?`, `what is the Quantum Collateral Index?`.
- In the Bulk view, set the created-date range to the last two months before you present, so the trend figures are on screen.
- Open the Audit view. Do not press Run scorecard until you reach that slide, since it takes a few minutes.

## 1. The problem (1 minute)

"Case comments in banking operations are full of abbreviations: KYC, PEP, LTV, DTI, CBS. A shift lead has to read five stages of comments to work out why a case is open or stalled.

In our timed trial, reviewing 20 cases by hand took about 20 minutes. That is about a minute per case, spent on reconstructing what happened.

Three people need something better. Priya needs one view per case. Managers need a trend report for a period. Auditors need to review a set of cases through trends and charts."

## 2. The idea (1 minute)

"CaseLens turns raw case data into grounded, plain-English answers.

Three rules shape it. First, the facts come from code. The model never does the arithmetic. Second, every line of model output must cite its source, and any line without a source is dropped and counted. Third, a person makes the decision. We log every thumbs-up and thumbs-down."

## 3. Live demo (4 minutes)

Each step matches one of the three user needs, or a control.

**Need 2: one-step case summary**
1. Type `summary of CS-2026-1001`. Point to the card: status, stage timeline, documents, SLA target, and priority, all on one screen. "Priya does not move between screens. Every line has a source in brackets."
2. Point to the thumbs up and down. "This is the human in the loop."

**Need 1: trend report for a period**
3. Open Bulk and show the created-date range for the last two months. Read out the open and stalled counts and the average turnaround. "Every number is computed from the data. The narrative only restates them, with citations."

**Need 3: audit by trend and chart**
4. Scroll to the charts: cases by type, average turnaround by type, longest stage per case, and stalled percentage by sub-type. "An auditor reviews a set of cases through these, not one case at a time."
5. Show the Excel export. "The same figures go to a workbook the auditor can keep."

**Controls**
6. Type `what is LTV?`. "It answers from the dictionary only."
7. Type `what is the Quantum Collateral Index?`. "It is not in the dictionary, so it says so. A chatbot that guesses here would be dangerous in a bank."
8. Open the Audit view. "Every model call is logged with its latency, tokens, and cost. The log stores counts and hashes, never the raw question or the key."

## 4. How we know it works (2 minutes)

Click Evaluation scorecard, then Run scorecard. While it runs, say:

"We do not ask you to trust the answers. We measure them."

When the table appears, read the headline rows:
- **Grounding:** 100%. Every summary line cites a source.
- **Invented terms refused:** 30 of 30.
- **Raw client IDs in output:** 0.
- **p95 latency:** about 2.5 seconds.

Then: "We also ran the live evaluation on the real model. Summaries passed 10 of 10, and chat passed 9 of 9. The test suite has 150 tests, and all pass."

## 5. Controls and cost (1 minute)

"Client details are masked before any model call. Questions about personal data are refused. The API key is kept in a local file, and we rotated it after the build.

Cost: one summary is about $0.0005 at the estimated price, so 1,000 summaries cost about 53 cents."

## 6. Limits and next steps (1 minute)

Say these yourself before the judges do:

- "The data is synthetic. A real deployment needs a data-protection review first."
- "We have not measured retrieval quality on real staff questions. We measured the 30 invented terms."
- "Chat answers are not cached yet. Summaries are."
- "The scorecard checks feedback counts only in the Audit view, not as a target."
- "The auditor view filters by period, type, and status. It does not yet filter by reviewer."

Then the next step: "Move the data to the bank's BPM database, add the data-protection review, and measure against real questions from shift staff."

## Technical overview: what is built (1 minute, or as a slide)

Say this accurately. Judges will test claims.

**Is it an agent?** No, not yet. "CaseLens is a grounded assistant, not an autonomous agent. It does not choose tools or take actions. Code decides how each question is answered, and the model only writes sentences about facts the code has already computed. Letting the model choose among tools is the next step, and it is on the roadmap."

**The technical terms, in plain words:**

| Term | What it means here |
|---|---|
| Rule-based question router | Fixed rules in `chat.py` decide whether a question is about a case ID, a glossary term, a trend, or out of scope. |
| Retrieval (RAG-style) | Glossary lookup. Terms are matched by whole phrase, and a semantic search (local sentence-embedding model, `all-MiniLM-L6-v2`) finds close terms. Retrieved entries are the only source the model may use. |
| Grounding | Every model line must cite a source ID (`[M#]`, `[C#]`, or `[JD-###]`). Lines without one are dropped. |
| Citation check | `keep_cited` in `summary.py` enforces grounding and counts what it drops. |
| Guardrails | Input checks (length, override phrases, PII questions), output masking, and a PII leak check on outgoing prompts. |
| Prompt injection defence | The question is treated as untrusted data. Override phrases are refused before any model call. |
| Template fallback | If the model is unavailable, a template summary is built from the same computed facts. |
| Deterministic metrics | Stage durations and turnaround computed in pandas from timestamps. No model arithmetic. |
| Summary cache | Repeat summaries for an unchanged case are served from memory, keyed by a hash of the prompt and model. |
| Prompt versioning | Each audit event records the prompt version, so changes can be compared. |
| Audit log | JSONL event log of model calls, blocks, cache hits, and feedback. Stores hashes and counts, never raw text or keys. |
| Human-in-the-loop | Thumbs up or down under each answer, logged as feedback. |
| Scorecard | Automated checks for grounding, invented-term refusal, PII leaks, and p95 latency. |
| Model | `openai/gpt-4o-mini` via OpenRouter, called over the OpenAI-compatible chat API, temperature 0. |

**If asked "why not an agent?":** "Agents add risk: a model that chooses its own tools can call the wrong one. For this use case, fixed routing with grounded explanation is safer and easier to audit. Tool choice is the next step, with every tool result cited."

## Q&A: likely questions

**Why not use a bigger model?** The model only explains facts that the code has already computed. A smaller model keeps the cost per summary low, and the citation check limits what it can say.

**What stops it making things up?** Three things: it can only use the dictionary, every line must cite a source, and an unknown term gets "not in the glossary". The scorecard tests the last one with 30 invented terms.

**Is any real data used?** No. All 500 cases and every name, account, and contact are synthetic.

**How much would this cost at scale?** About $0.0005 per summary at the estimated price. Infrastructure is not estimated yet.

**What happens when the model is down?** The app falls back to a template summary, built from the same computed facts, and says the model was not used.

**What did you get wrong?** One valid question was refused until a fix. A time-to-stage answer printed "nan" until a fix. We found both in the live run and fixed them. The failures are listed in the risk register.

**Can a manager get open and stalled counts for last month?** Yes, in the Bulk view, by setting the created-date range. Open and stalled counts and average turnaround are shown for that range.

**Who owns the decisions?** The shift lead. CaseLens gives a summary and a source. It does not approve or close a case.
