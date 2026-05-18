# Evaluation and Metrics

## Quality Signals
- Helpfulness score from user feedback.
- Safety compliance (no fabricated assets or guarantees).
- Profile consistency in recommendations.
- Correct transaction extraction and logging.
- End-to-end response latency.
- CSV ingestion accuracy for dashboard updates.
- Language consistency (English-first output).

## Validation Layers
1. Automated tests in tests/.
2. Runtime event logs in data/runtime/events.jsonl.
3. Manual scenario checks for critical prompts.

## Suggested KPIs for Demo/Production
- Successful login rate.
- OTP/send-code error rate.
- Message-to-response success rate.
- Median first-response latency.
- CSV upload success rate.
- Session restore success rate.

## Current Focus
- English-only responses.
- Stable provider fallback behavior.
- Improved transaction parsing reliability.
- Reliable dashboard refresh after chat/CSV state updates.
