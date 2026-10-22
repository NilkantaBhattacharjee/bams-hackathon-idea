# CaseLens: Submission Pack Index

Status as of 22 Oct 2026. Items marked **Open** need action before submission.

| # | Handoff deliverable | File | Status | What is still needed |
|---|---|---|---|---|
| 1 | Problem statement, persona, KPIs | `01_problem_statement.md` | Done | Baseline is measured (20-case timed trial) |
| 2 | Architecture diagram | `05_architecture.md` | Done | Mermaid diagram; renders in GitHub, VS Code preview, or mermaid.live |
| 3 | Working demo | `05_architecture.md` (Deployment) | Done | Browser check passed (22 Oct 2026); run `py -m streamlit run app.py` to repeat |
| 4 | Evaluation results | Evaluation scorecard page; `eval/live_results.md` | Done | Live evaluation passed: summaries 10/10, chat 9/9, trend narrative passed (22 Oct 2026) |
| 5 | Risk register and control notes | `02_risk_register.md` | Done | API key rotated (R7 updated) |
| 6 | Cost estimate | `03_cost_estimate.md` | Done | Price is set; confirm it against the model page before submission |
| 7 | Monitoring plan | `04_monitoring_plan.md` | Done | None |

## Demo checklist (browser)

1. Home: top row shows Home, Audit view, Evaluation scorecard. Single and Bulk are the options. | Done | PASS |
2. Chat: ask "summary of CS-2026-1001". Thumbs up and down appear under the card. | Done | PASS |
3. Single or Bulk: the "⬅ Back" button returns to the options. | Done | PASS |
4. Audit view: chat hidden. Cache, cost, and feedback cards show. | Done | PASS |
5. Evaluation scorecard: press "Run scorecard". Pass or fail per row. | Done | PASS |

## Evidence to attach

- Scorecard table (grounding 100%, invented terms refused 100%, raw client IDs 0, p95 latency 2.5 s).
- Timed trial: 20 cases, 20 min manual vs 7 to 8 min with CaseLens.
- Live evaluation report (`eval/live_results.md`) after the re-run.
- Test suite result: 150 of 150 passing (22 Oct 2026, latest full run).

## Before you submit

1. Done: OpenRouter key rotated, old key disabled.
2. Done: live evaluation re-run and recorded (`eval/live_results.md`).
3. Done: demo checklist checked in a browser; all five items pass.
4. Done: R7 updated in the risk register after the key rotation.
