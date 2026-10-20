# CaseLens: Monitoring Plan

## What is monitored

| Signal | Source | Where to see it | Alert condition |
|---|---|---|---|
| Grounding (cited share of lines) | Scorecard | Evaluation scorecard page | Below 95% |
| Invented terms refused | Scorecard, 30-term check | Evaluation scorecard page | Below 100% |
| Raw client IDs in output | Scorecard | Evaluation scorecard page | Above 0 |
| p95 latency per model call | Audit log | Audit view | Above 5 s |
| Tokens and estimated cost per call | Audit log and price setting | Audit view | Cost trend rising week on week |
| Real errors (model or system failures) | Audit log | Audit view, "Real errors" card | Any non-zero count |
| Guardrail blocks (PII, injection) | Audit log | Audit view, "Guardrail blocks" card | Sudden rise |
| Dropped lines (citation check) | Audit log | Audit view | Sudden rise |
| Prompt-version comparison | Audit log | Audit view | Latency or dropped lines worse on a new prompt version |
| Human feedback (helpful share) | Audit log, feedback events | Audit view | Helpful share below the agreed threshold |

## Review cadence

- **Each change to prompts, routing, or data:** re-run the scorecard and the test suite before release.
- **Weekly:** review the Audit view. Check real errors, cost, p95 latency, and helpful share.
- **Monthly:** check the model's listed price and update `OPENROUTER_PRICE_PER_1K_TOKENS`. Re-check the API key rotation status.

## Owners

- Product owner: sets the KPI targets and reviews feedback.
- Developer: runs the scorecard after changes and fixes failures.
- Shift lead (user): gives thumbs up or down and reports wrong answers.

## Incident response

1. A scorecard check fails: stop the release, find the cause (the invented-term check names the term), and fix before re-running.
2. Guardrail blocks spike: check whether a new question pattern or an attack is in the log. Do not log the raw question.
3. Real errors appear: check the model status and the API key, then re-run one case.

## Data handling

The audit log stores hashes, IDs, and counts only. It never stores the raw question, the API key, or client details.
