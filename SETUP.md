# Setup Guide - Pluto Finance AI

## Prerequisites

- Python 3.11 or newer
- Git
- Optional: Supabase project for authentication and cloud state persistence

## 1) Create and Activate a Virtual Environment

Windows PowerShell:

```bash
python -m venv .venv
. .venv/Scripts/activate
```

## 2) Install Dependencies

```bash
pip install -r requirements.txt
```

## 3) Configure Environment Variables

```bash
copy .env.example .env
```

Then edit `.env` with your real values:

- `OPENROUTER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_EMAIL_REDIRECT_TO` (for local: `http://localhost:8501`)

## 4) Run the App Locally

```bash
python -m streamlit run src/app.py
```

## 5) Run Tests

```bash
python -m pytest tests/ -q
```

## Authentication Modes

- `AUTH_REQUIRED=true`: Supabase OTP/magic-link flow is enforced.
- `AUTH_REQUIRED=false` and `EMAIL_LOGIN_REQUIRED=true`: simplified email-only local/dev flow.
- `EMAIL_LOGIN_REQUIRED=false`: no email gate (only recommended for isolated development scenarios).

## Security Notes

- Never commit `.env`.
- Rotate any exposed provider key immediately.
- Keep production values in your deployment platform (Render), not in source files.
