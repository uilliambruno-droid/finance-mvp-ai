# Pluto Finance AI

Pluto Finance AI is a conversational financial assistant focused on practical financial education, budgeting, and investment guidance for Brazil-first scenarios.

## Key Features
- Mandatory profile intake before chat.
- Passwordless email login with Supabase and local fallback state.
- Persistent profile, messages, and transactions per user.
- Natural-language transaction capture for income and expenses.
- Goal tracking with progress and monthly target estimate.
- Scenario-aware financial guidance and risk warnings.
- OpenRouter primary LLM path with optional Ollama fallback.

## Stack
- Python 3.11+
- Streamlit
- Pandas
- Requests
- python-dotenv

## Run
```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
streamlit run src/app.py
```

## Safety Scope
- Educational content only.
- No execution of real financial operations.
- No request for sensitive credentials.
