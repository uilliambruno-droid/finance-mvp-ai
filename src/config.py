"""Configuration and constants for Pluto Finance AI."""

import os
from pathlib import Path
from typing import Any

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
RUNTIME_DIR = DATA_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "user_state.json"
EVENTS_LOG_FILE = RUNTIME_DIR / "events.jsonl"

# LLM Configuration
LLM_MAX_OUTPUT_TOKENS = max(64, int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1000")))
LLM_CONTEXT_RECENT_MESSAGES = max(2, int(os.getenv("LLM_CONTEXT_RECENT_MESSAGES", "4")))
LLM_CONTEXT_TOP_CATEGORIES = max(1, int(os.getenv("LLM_CONTEXT_TOP_CATEGORIES", "3")))
LLM_CONTEXT_PRODUCTS = max(2, int(os.getenv("LLM_CONTEXT_PRODUCTS", "6")))

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-1.2b-instruct:free")
OPENROUTER_URL = os.getenv(
    "OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions"
)
OPENROUTER_TIMEOUT_SECONDS = max(10, int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30")))
OPENROUTER_MAX_RETRIES = max(0, int(os.getenv("OPENROUTER_MAX_RETRIES", "2")))
OPENROUTER_RETRY_BASE_SECONDS = max(
    1.0, float(os.getenv("OPENROUTER_RETRY_BASE_SECONDS", "1.2"))
)

# Ollama Configuration (Fallback LLM)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct")
DISABLE_OLLAMA = os.getenv("DISABLE_OLLAMA", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Supabase Configuration (Auth & Persistence)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_USER_STATES_TABLE = os.getenv("SUPABASE_USER_STATES_TABLE", "user_states")
SUPABASE_EMAIL_REDIRECT_TO = os.getenv("SUPABASE_EMAIL_REDIRECT_TO", "")

# Authentication Settings
OTP_COOLDOWN_SECONDS = int(os.getenv("OTP_COOLDOWN_SECONDS", "60"))
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
EMAIL_LOGIN_REQUIRED = os.getenv("EMAIL_LOGIN_REQUIRED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# UI Styling
HIDE_STREAMLIT_CHROME = """
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppToolbar {display: none;}
    [data-testid="stToolbar"] {display: none;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stChatMessageAvatar"] {display: none;}
    [data-testid="stChatMessageContent"] {margin-left: 0 !important;}
</style>
"""

# UI Texts (English-only)
TEXTS = {
    "en": {
        "caption": "A conversational financial assistant designed to support each person at their own pace.",
        "intake_title": "Before chat, let's build your financial profile quickly.",
        "intake_caption": (
            "Fill out the form once and Pluto unlocks chat with your context. "
            "No need to keep asking for your name."
        ),
        "intake_submit": "Unlock chat with my profile",
        "intake_name": "Name",
        "intake_has_income": "I have monthly income",
        "intake_income": "Approximate monthly income (R$)",
        "intake_profile": "Investor style",
        "intake_profile_conservative": "Conservative",
        "intake_profile_moderate": "Moderate",
        "intake_profile_aggressive": "Aggressive",
        "intake_spending": "Approximate monthly expenses (R$)",
        "intake_has_spending": "I have fixed expenses / recurring spending",
        "intake_current_wealth": "Current net worth (R$)",
        "intake_target_wealth": "Target net worth (R$)",
        "intake_target_deadline_months": "Target deadline (months)",
        "intake_goal_progress": "Goal progress",
        "intake_target_deadline_label": "Deadline",
        "intake_target_monthly_needed_label": "Required monthly contribution",
        "wealth_current_label": "Net worth",
        "wealth_target_label": "Target",
        "wealth_missing_label": "Missing",
        "intake_income_source": "Income source",
        "intake_notes": "Notes",
        "intake_ready_title": "Profile loaded",
        "intake_ready_caption": (
            "Chat is now unlocked with your context. Pluto already knows the basics "
            "and can jump straight into consulting."
        ),
        "intake_missing_warning": "Fill all fields to unlock chat.",
        "intake_all_required_warning": "All form fields are required in this prototype.",
        "intake_deadline_warning": "Set a deadline in months for your net worth target.",
        "consultant_welcome": "Perfect. I have your profile now and can speak like a financial consultant, no fluff.",
        "chat_locked": "Before I unlock chat, I need a minimal profile so I can personalize the answers.",
        "welcome": "Hi! I'm Pluto 🪐 What is your name?",
        "welcome_quick": (
            "Hi! I'm Pluto 🪐 Tell me directly what you want to solve today "
            "in your Brazil-focused finances."
        ),
        "brazil_focus_notice": (
            "🇧🇷 We are moving to a Brazil-only focus: products, rules, and "
            "financial education prioritize the Brazilian context. I can reply "
            "in English, but the content remains Brazil-first."
        ),
        "english_toggle_label": "Reply in English / Responder em inglês",
        "chat_mode_label": "Conversation mode",
        "chat_mode_guided": "Guided (Pluto asks and structures with you)",
        "chat_mode_quick": "Quick (straight to the point)",
        "state_restored": "Previous session restored successfully.",
        "state_restore_error": "I couldn't restore your previous session; we can continue from here.",
        "state_save_error": "I couldn't save session state right now.",
        "chat_placeholder": "Talk to Pluto about planning, spending, income, or investing...",
        "csv_title": "Want to send your spending data?",
        "csv_caption": (
            "If you prefer, you can upload a CSV with your transactions and "
            "I'll analyze your spending without making you fill out a form."
        ),
        "upload_label": "Upload transactions CSV",
        "upload_help": "Accepted columns: data/date, valor/amount, categoria/category, tipo/type.",
        "upload_success": "CSV uploaded successfully. I can use this data in the next answers.",
        "upload_error": "I couldn't read that CSV. Please check the file and try again.",
        "profile_summary": "What I already understand about you",
        "profile_empty": "I'm still getting to know you.",
        "metrics_profile": "Context mapped",
        "metrics_interactions": "Interactions",
        "metrics_transactions": "Transactions",
        "feedback_title": "Did this answer help?",
        "feedback_positive": "Helpful",
        "feedback_negative": "Not yet",
        "feedback_saved": "Thanks for the feedback — I'll use it to improve Pluto.",
        "feedback_rating_label": "Rating (1–5)",
        "feedback_comment_label": "Want to add a note? (optional)",
        "feedback_comment_placeholder": "E.g.: missing detail on X, or: perfect answer!",
        "feedback_submit": "Send feedback",
        "price_unavailable": "I couldn't fetch live prices right now. If you want, I can try again in a moment.",
        "price_snapshot_title": "📈 Quick market snapshot",
        "risk_warning": (
            "📌 Note: educational content only, not professional investment advice. "
            "Market assets can fluctuate and lead to losses."
        ),
        "unknown_assets": (
            "⚠️ Safety note: I found assets outside the current catalog ({assets}). "
            "I can explain them educationally, but I won't recommend "
            "uncatalogued assets."
        ),
        "investor_context": (
            "Investor profile context: {profile}. If you want, I can adapt the "
            "answer to a more conservative or more aggressive style."
        ),
        "fallback_greeting": (
            "Hi! I'm doing well too 🪐 I can't reach the model right now, but I can "
            "still help with planning, spending, and next steps."
        ),
        "fallback_general": (
            "I can't reach the model right now, but I can still help. Tell me what "
            "you want to analyze and I'll work with the information I have."
        ),
        "short_answer": " Tell me a bit more about what you want to solve so I can answer more precisely.",
        "rate_limit_notice": (
            "⚠️ The consultation limit for this moment has been reached. Please wait "
            "a bit and try again, or contact the developer for a plan with more "
            "requests."
        ),
        "followup_goal": (
            "If it helps, tell me what your main financial goal is right now. "
            "That helps me guide you better."
        ),
        "followup_income_source": (
            "If you want, you can also tell me how your income comes in today: "
            "salary, freelance work, your own business, or no income right now."
        ),
        "followup_income_amount": (
            "If you're comfortable sharing it, your monthly income helps me suggest "
            "more realistic priorities and goals."
        ),
        "followup_profile": (
            "If you want, I can also adapt my answers to your risk style - more "
            "conservative, moderate, or aggressive."
        ),
        "followup_csv": (
            "And if it's easier, you can upload a CSV with your spending right below "
            "so I can analyze everything from the data."
        ),
        "followup_name": "Before we continue, what is your name?",
        "unemployment_support": (
            "If you're unemployed or without income right now, the first priority "
            "does not need to be investing. I can help you organize essential "
            "spending, think about income options, and build a simple plan without "
            "losing momentum."
        ),
        "no_income_prompt": (
            "For now, it makes sense to prioritize cash, essential expenses, and "
            "ways to generate income before thinking about financial risk."
        ),
        "updated_profile": "I noted this about you: {fields}.",
        "transaction_recorded": "Recorded: **{tipo}** of **R$ {valor:.2f}** in **{categoria}** ({data}).",
        "transaction_recorded_caption": "Logged to your history. You can keep chatting normally.",
        "edit_profile": "Edit profile",
        "login_title": "🪐 Pluto Finance AI",
        "login_caption": "Email login (passwordless).",
        "login_language_label": "Language",
        "login_email_label": "Email",
        "login_email_placeholder": "you@email.com",
        "login_send_code": "Send access code",
        "login_invalid_email": "Please enter a valid email to continue.",
        "login_magic_link_hint": "If the email link does not open correctly, use the 6-digit code below.",
        "login_wait_before_resend": "Wait {seconds}s before requesting a new code to avoid rate limiting.",
        "login_code_sent": "Code sent to your email. Enter it below to sign in.",
        "login_otp_label": "Code received by email",
        "login_otp_placeholder": "123456",
        "login_submit": "Sign in",
        "login_bypass_notice": "Login disabled in this environment (AUTH_REQUIRED=false).",
        "prototype_notice": "Prototype in progress: responses and UI may change while we validate features.",
        "prototype_legal_notice": (
            "Legal notice: this prototype does not provide official financial advice. "
            "We are not responsible for decisions based on responses or for personal "
            "data entered into the system."
        ),
        "login_email_only_caption": "Quick email access (token validation temporarily disabled).",
        "login_continue": "Continue",
        "logout_button": "Log out",
        "clear_data_button": "Clear data",
        "clear_data_success": "Your local data has been cleared successfully.",
        "clear_data_error": "I couldn't clear your data right now.",
        "developer_link": "About the developer",
        "developer_modal_title": "Developed by Uilliam",
        "developer_bio": (
            "I am Uilliam Santos, the developer behind this Pluto Finance AI "
            "prototype, focused on building simple and useful experiences for "
            "financial education."
        ),
        "developer_contacts": "Contacts",
        "developer_email_label": "Email",
        "developer_phone_label": "WhatsApp / Phone",
        "developer_linkedin_label": "LinkedIn",
    },
}


def get_texts(language: str) -> dict[str, Any]:
    """Get UI texts for a specific language."""
    return TEXTS.get(language, TEXTS["en"])
