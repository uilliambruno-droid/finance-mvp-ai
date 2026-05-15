# Evaluation and Metrics

## Quality Signals
- Helpfulness score from user feedback.
- Safety compliance (no fabricated assets or guarantees).
- Profile consistency in recommendations.
- Correct transaction extraction and logging.
- End-to-end response latency.

## Validation Layers
1. Automated tests in tests/.
2. Runtime event logs in data/runtime/events.jsonl.
3. Manual scenario checks for critical prompts.

## Current Focus
- English-only responses.
- Stable provider fallback behavior.
- Improved transaction parsing reliability.
