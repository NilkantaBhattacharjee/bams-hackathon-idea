# CaseLens: Problem Statement

## Persona

**Priya, shift lead in a retail banking operations team.** She manages about 40 BPM cases a shift across mortgages, personal loans, and credit card disputes. She has to explain to managers why a case stalled, and she reads long comment trails written in abbreviations (KYC, PEP, LTV, DTI, CBS, STP and many more).

## Problem

- Case comments are dense, abbreviated, and spread across five stages.
- Reconstructing why a case is open or stalled is slow. In a timed trial of 20 cases, the manual way took about 20 minutes in total (about 1 minute per case).
- Managers and auditors ask for trends, and the answers come from manual reading from case details.
- Shift handovers lose context when a case changes hands.
- Priya has to open several screens to get one case's status, stages, and documents, which takes time she does not have.
- Managers need to know, for any period (for example the last one or two months), how many cases are still open or stalled and what the average turnaround is. This is not available quickly today.
- Auditors need to review a set of cases by looking at trends and charts, not reading each case one by one.

## Solution

CaseLens turns raw case data into grounded, plain-English answers:
- A case card with a stage timeline, documents, SLA target, and jargon explained.
- A bulk view with trends, charts, SLA breaches, and an Excel export.
- A chat that answers case and jargon questions and refuses anything outside the data.

The three user needs CaseLens meets:
1. **Trend report over a chosen period.** Pick a date range (for example the last one or two months) and see how many cases are open, stalled, or closed, and the average turnaround. The Bulk view does this with a created-date filter.
2. **One-step case summary.** Priya enters a case ID, or asks "summary of CS-2026-1001", and gets the card with status, stages, documents, SLA, and jargon in one view. She does not move between screens.
3. **Audit by trend and chart.** An auditor reviews a set of cases through the Bulk charts and trend figures, filtered by period, type, and status. The Audit view shows how the tool itself has been used.

Facts come from code. The model only explains computed facts. Every claim cites a source.

## Numeric KPIs

These are the targets the scorecard checks. Figures are from the scorecard run on the current 500-case dataset.

| KPI | Target | Measured |
|---|---|---|
| Grounding: cited lines as share of all summary lines | 95% or more | 100% (5,808 of 5,808) |
| Invented terms refused or not defined | 100% | 100% (30 of 30) |
| Raw client IDs in outgoing output | 0 | 0 |
| p95 latency per model call | under 5 s | 2.5 s (178 calls) |
| Need 1: open and stalled counts with average turnaround for a chosen period | Shown for any date range in one view | Met: Bulk view filters by created date and shows open, stalled, and average TAT for that range |
| Need 2: one-step case summary | One view, no screen changes | Met: a case ID returns the card, with status, stages, documents, SLA, and jargon |
| Need 3: audit by trend and chart | Charts and trend figures for any selected set of cases | Met: Bulk charts and trend report; Audit view for how the tool was used |
| Time to review a case, 20-case timed trial | 40% or less of manual time (proposed target) | 35 to 40% of manual time: 7 to 8 min with CaseLens vs 20 min manual, about 0.4 min vs 1 min per case (60 to 65% faster) |

## Out of scope

- Real customer data. All cases are synthetic.
- Automated decisions. Output is decision support only; a human decides.
- Live integration with the BPM system.
