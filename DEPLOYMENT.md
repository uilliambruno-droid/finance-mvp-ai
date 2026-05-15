# Deployment Guide - Pluto Finance AI

## Pre-Deployment Checklist ✅

- [x] All tests passing (20 passing)
- [x] Code compiled without errors
- [x] TEXTS['pt'] removed (English-only)
- [x] LLM_MAX_OUTPUT_TOKENS updated to 1000
- [x] render.yaml configured with production values
- [x] .env.example updated with correct defaults
- [x] All response post-processing cleaned up
- [x] Documentation updated

## Production Environment Variables

### Required Variables
These **MUST** be set in your Render dashboard:

1. **OPENROUTER_API_KEY** - Your OpenRouter API key (https://openrouter.ai)
   - Get keys at: https://openrouter.ai/keys

2. **SUPABASE_URL** - Supabase project URL
   - Format: `https://xxx-xxxxx.supabase.co`

3. **SUPABASE_ANON_KEY** - Supabase anonymous key (public, safe to expose)

4. **SUPABASE_EMAIL_REDIRECT_TO** - Email callback URL for Supabase auth
   - For Render: `https://your-app-name.onrender.com`

5. **AUTH_REQUIRED** (optional, defaults to true)
   - Set to `true` to require email login
   - Set to `false` for open access

### Optional but Recommended
- **SUPABASE_ALLOWED_EMAILS** - Comma-separated list of allowed emails
  - Example: `user1@example.com,user2@example.com`
  
- **SUPABASE_ALLOWED_DOMAINS** - Comma-separated list of allowed domains
  - Example: `company.com,partner.com`

## Deployment Steps

### 1. Push to Git
```bash
git add .
git commit -m "Refactor and prepare for production"
git push
```

### 2. Deploy to Render
1. Go to https://dashboard.render.com
2. Create a **New Web Service**
3. Select your GitHub repository
4. Configure:
   - **Name**: pluto-finance-ai
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - **Plan**: Free (or higher if needed)

### 3. Set Environment Variables in Render
In your Render service dashboard, go to **Environment** and add:
- `OPENROUTER_API_KEY` (sync: false)
- `SUPABASE_URL` (sync: false)
- `SUPABASE_ANON_KEY` (sync: false)
- `SUPABASE_EMAIL_REDIRECT_TO=https://your-service-name.onrender.com`
- `ENVIRONMENT=production`
- `DISABLE_OLLAMA=true`

### 4. Deploy Configuration Files
The `render.yaml` contains production-ready settings. Deploy will automatically use:
- `LLM_MAX_OUTPUT_TOKENS=1000` (for complete responses)
- `OPENROUTER_MODEL=openrouter/auto` (automatic routing)
- `OPENROUTER_TIMEOUT_SECONDS=30`
- `DISABLE_OLLAMA=true` (no local fallback in production)

### 5. Monitor Logs
```bash
# In Render dashboard, go to "Logs" to monitor:
- Streamlit server startup messages
- LLM API call errors
- User authentication issues
- State persistence errors
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

## Production Monitoring

### Key Metrics to Watch
- **Startup time**: Should complete in <30s
- **First response time**: Typically 2-10s depending on LLM latency
- **Subsequent responses**: 1-5s
- **Error rate**: Should be <1%

### Common Issues & Fixes

#### Issue: Email OTP not sending
- **Cause**: Supabase email provider not configured
- **Fix**: Enable Email OTP in Supabase → Authentication → Providers → Email

#### Issue: Responses still truncated
- **Cause**: Wrong LLM_MAX_OUTPUT_TOKENS value
- **Fix**: Verify in render.yaml: `LLM_MAX_OUTPUT_TOKENS=1000`

#### Issue: Login redirects to wrong URL
- **Cause**: SUPABASE_EMAIL_REDIRECT_TO mismatch
- **Fix**: Update to match your actual Render URL (https://xxx.onrender.com)

#### Issue: State not persisting
- **Cause**: Supabase URL or key incorrect
- **Fix**: Double-check `SUPABASE_URL` and `SUPABASE_ANON_KEY` in Render dashboard

## Performance Optimization

### For Faster Responses
1. Increase `LLM_CONTEXT_RECENT_MESSAGES` in render.yaml for better context
2. Consider upgrading to Render's Standard plan if free tier is slow
3. Monitor OpenRouter costs and consider using `gpt-4o-mini` for cost optimization

### For Better Security
1. Enable `SUPABASE_ALLOWED_EMAILS` to restrict access
2. Keep `AUTH_REQUIRED=true` in production
3. Rotate API keys regularly
4. Monitor for suspicious access patterns in Render logs

## Rollback Procedure

If deployment has critical issues:
1. Go to Render dashboard → your service
2. Click **Suspensions/History**
3. Select a previous working version
4. Click **Redeploy**

## Future Scaling

As usage grows:
1. Upgrade Render plan (Standard, Pro)
2. Consider database optimization for Supabase
3. Implement response caching for common queries
4. Use Render's PostgreSQL addon if Supabase becomes bottleneck

---

**Last Updated**: May 15, 2026  
**Status**: Ready for Production ✅
