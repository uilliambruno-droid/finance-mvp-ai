# Application Code

This folder contains the executable Pluto Streamlit application.

## Files
- app.py: Main Streamlit UI, orchestration, auth, and model calls.
- finance_knowledge.py: Financial guidance and transaction extraction helpers.

## Current Capabilities
- Loads profile, transactions, products, and support history data.
- Builds user context for grounded LLM responses.
- Supports OpenRouter primary path and Ollama fallback.
- Adds post-response safety notes for risk and out-of-catalog assets.
- Persists runtime state and event logs.

## Run Locally
```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r ../requirements.txt
streamlit run app.py
```
