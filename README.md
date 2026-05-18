# Pluto Finance AI

Pluto Finance AI is a conversational financial assistant for practical financial education, budgeting, and planning in a Brazil-first context.

## What It Does

- Collects a mandatory user profile before enabling chat.
- Supports email-based authentication and user state persistence.
- Extracts income and expense transactions from natural language.
- Accepts CSV uploads and updates dashboard financial indicators.
- Tracks net-worth goals, progress, and estimated monthly contribution.
- Uses OpenRouter as primary LLM with optional Ollama fallback.

## Architecture (Current)

- `src/app.py`: main orchestration and Streamlit page lifecycle.
- `src/config.py`: central configuration and UI text dictionary.
- `src/ui_auth.py`: authentication UI flow.
- `src/ui_profile.py`: profile intake, dashboard, CSV ingestion.
- `src/ui_chat.py`: chat rendering, feedback, and user-turn processing.
- `src/profile.py`: profile domain logic.
- `src/state.py`: persistence and state serialization helpers.
- `src/context_builder.py`: LLM context/message assembly.
- `src/finance_knowledge.py`: knowledge helpers and transaction extraction.
- `src/response_processing.py`: response post-processing safeguards.
- `src/llm.py`: provider calls and retry/fallback logic.
- `src/auth.py`: Supabase auth API wrappers.

## Tech Stack

- Python 3.11+
- Streamlit
- Pandas
- Requests
- python-dotenv
- Supabase (auth and persistence)

## Quick Start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python -m streamlit run src/app.py
```

## Testing

```bash
python -m pytest tests/ -q
```

## Deployment

- Render configuration: `render.yaml`
- Full deployment runbook: `DEPLOYMENT.md`

## Safety Scope

- Educational guidance only (not official financial advice).
- No direct execution of financial operations.
- No collection of secret credentials inside chat.
