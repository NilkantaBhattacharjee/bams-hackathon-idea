# CaseLens: Risk Register and Control Notes

| ID | Risk | Likelihood | Impact | Control in place | Residual risk |
|---|---|---|---|---|---|
| R1 | Model invents a definition for an unknown term | Medium | High | Glossary-only answers; partial-match refusal; 30-term invented-term check in the scorecard | Low |
| R2 | Personal or account data sent to the model | Low | High | PII masking before every model call; PII questions refused; PII leak check (0 raw IDs in output) | Low |
| R3 | Prompt injection in case comments or questions | Medium | Medium | Input scan for override phrases; comments treated as data; output citation check | Low to medium |
| R4 | Uncited or unsupported sentence reaches the user | Medium | Medium | Citation check drops any line without a valid source (286 lines dropped in logged runs) | Low |
| R5 | Cost overrun from model calls | Medium | Medium | Token count logged per call; price setting shows cost per call and per case; cost by case table | Medium until a real price is set |
| R6 | Stale or wrong figures after data changes | Medium | Medium | Figures computed from the CSV on each run; scorecard re-run after data changes | Low |
| R7 | API key exposed | Medium | High | Key in `.env`, not in code; never written to the audit log; key rotated on 22 Oct 2026 and the old key disabled | Low |
| R8 | Users over-trust the answer | Medium | High | Decision-support label on every card; thumbs up/down feedback; human makes the final decision | Medium |
| R9 | Prompt change degrades answers unnoticed | Medium | Medium | Prompt version logged on every event; prompt-version comparison in the Audit view | Low |

## Open actions

1. Done: OpenRouter API key rotated and the old key disabled (R7). The live evaluation on the new key passed.
2. Set `OPENROUTER_PRICE_PER_1K_TOKENS` to the price confirmed on the model page (R5).
3. Re-run the scorecard after any change to prompts, routing, or data (R1, R4, R6).
4. Review feedback counts in the Audit view each week (R8).
