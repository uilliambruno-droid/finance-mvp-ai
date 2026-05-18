# Deployment Guide - Pluto Finance AI

## Pre-Deployment Checklist

- Tests passing locally (`python -m pytest tests/ -q`)
- App starts locally (`python -m streamlit run src/app.py`)
- No critical lint/diagnostic errors in `src/`
- `render.yaml` start command points to `src/app.py`
- Sensitive keys are stored only in Render environment variables

## Production Environment Variables

Set these variables in Render Dashboard -> Environment.

### Required

1. `OPENROUTER_API_KEY`
2. `SUPABASE_URL`
3. `SUPABASE_ANON_KEY`
4. `SUPABASE_EMAIL_REDIRECT_TO`
5. `ENVIRONMENT=production`
6. `DISABLE_OLLAMA=true`

### Recommended

1. `OPENROUTER_MODEL=openrouter/auto`
2. `LLM_MAX_OUTPUT_TOKENS=1000`
3. `LLM_CONTEXT_RECENT_MESSAGES=4`
4. `LLM_CONTEXT_TOP_CATEGORIES=3`
5. `LLM_CONTEXT_PRODUCTS=6`
6. `AUTH_REQUIRED=true` (or `false` for temporary demo mode)
7. `EMAIL_LOGIN_REQUIRED=true`
8. `SUPABASE_ALLOWED_EMAILS` and/or `SUPABASE_ALLOWED_DOMAINS`

## Deployment Steps

### 1) Push to GitHub

```bash
git add .
git commit -m "Prepare production deploy"
git push origin main
```

### 2) Create/Update Render Web Service

1. Go to https://dashboard.render.com
2. Create a new Web Service (or open the existing one)
3. Select your GitHub repository
4. Configure:
   - Name: `pluto-finance-ai`
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

### 3) Deploy

- Trigger deploy from latest `main` commit.
- Wait until Render status is `Live`.

### 4) Monitor Logs

```bash
# In Render -> Logs, monitor:
# - Streamlit startup output
# - OpenRouter failures/timeouts
# - Supabase authentication errors
# - State persistence errors
```

## Verifying Production Setup

### Test Email Login

1. Visit your deployed URL: `https://your-service-name.onrender.com`
2. Enter test email
3. Check email for OTP code
4. Verify login works and state persists

### Test LLM Responses

1. Fill out profile intake form
2. Send test messages like:
   - "I make R$ 5000/month"
   - "What should I invest in?"
   - "How much should I save?"
3. Verify responses are complete (no truncation)
4. Verify no excessive post-processing appends

### Test State Persistence

1. Fill profile and chat
2. Refresh page (F5)
3. Verify profile and chat history remains

### Test CSV Upload Flow

1. Upload a transactions CSV.
2. Confirm dashboard values are updated.
3. Confirm assistant posts a finance-updated message.

## Troubleshooting

### `File does not exist: app.py`

- Cause: wrong start command path.
- Fix: use `src/app.py` in Render start command.

### OTP/Email rate-limit issues during demo

- Temporary workaround for demos:
   - `AUTH_REQUIRED=false`
   - `EMAIL_LOGIN_REQUIRED=true`
- This keeps a simple email gate and avoids OTP send limits.

### Login redirect mismatch

- Ensure `SUPABASE_EMAIL_REDIRECT_TO` matches your public Render URL.

### State not persisting

- Recheck `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and table permissions.

## Rollback Procedure

If deployment has critical issues:
1. Go to Render dashboard → your service
2. Open deployment history
3. Select a previous working version
4. Redeploy that version

---

Last Updated: May 18, 2026
