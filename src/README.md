# Source Code Guide

This folder contains the production Streamlit application and all domain modules.

## Module Overview

- `app.py`: top-level orchestration and app lifecycle.
- `config.py`: constants, environment values, and UI text resources.
- `ui_auth.py`: login/auth UI screens and access gate.
- `ui_profile.py`: profile intake, dashboard cards, CSV upload handling.
- `ui_chat.py`: chat timeline, feedback UI, user-turn execution.
- `auth.py`: Supabase auth API wrappers.
- `profile.py`: profile data model and update extraction logic.
- `state.py`: persistence utilities and transaction normalization.
- `llm.py`: OpenRouter/Ollama provider integration.
- `context_builder.py`: structured prompt/context assembly.
- `finance_knowledge.py`: financial knowledge helpers and transaction parsing.
- `response_processing.py`: response validation and guardrails.

## Design Principles

- Keep UI concerns isolated in `ui_*` modules.
- Keep profile/state/business logic in domain modules.
- Keep LLM interactions deterministic and observable.
- Preserve compatibility for integration tests that import from `app`.

## Local Run

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r ../requirements.txt
python -m streamlit run app.py
```
