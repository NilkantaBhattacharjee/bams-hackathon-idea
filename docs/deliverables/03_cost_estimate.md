# CaseLens: Cost Estimate

## Basis

- Model: `openai/gpt-4o-mini` via OpenRouter.
- Listed price on the model page: $0.15 per million input tokens, $0.60 per million output tokens (checked on 20 Oct 2026).
- The app logs one total token count per call, so the estimate uses the average of the two prices: $0.375 per million, which is $0.000375 per 1K tokens.
- This is a conservative figure. Prompts are longer than replies, so real cost is likely closer to the input price.

## Measured usage (audit log, current runs)

| Measure | Value |
|---|---|
| Model calls logged | 850 |
| Average tokens per call | 1,399 |
| Total tokens logged | 39,180 |
| Estimated cost at $0.000375 per 1K | about $0.0147 for all logged calls |

Logged runs include test runs. Production usage will differ.

## Per-summary estimate

| Item | Estimate |
|---|---|
| Tokens per single-case summary (one call) | about 1,400 |
| Cost per summary at $0.000375 per 1K | about $0.0005 |
| Cost per 1,000 summaries | about $0.53 |

## Cost controls

- The price setting is read from `.env`. The Audit view shows cost per call, total cost, and cost by case.
- Template answers (no model call) cost nothing, and the offline scorecard makes no model calls.
- The model is called only for summaries and free-form chat questions, not for every click.

## Gaps

- Input and output tokens are logged as one total, so the estimate is approximate.
- The price comes from the model page on one date and may change.
