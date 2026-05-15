from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Import configuration constants
from config import (
    BASE_DIR,
    DATA_DIR,
    DOCS_DIR,
    EVENTS_LOG_FILE,
    HIDE_STREAMLIT_CHROME,
    RUNTIME_DIR,
    STATE_FILE,
    TEXTS,
)
from finance_knowledge import load_tax_knowledge

# Import from modular components
from profile import (
    apply_profile_form_submission,
    default_user_profile,
    extract_profile_updates,
    format_goal_timeline,
    format_profile_summary,
    format_update_fields,
    goal_progress,
    next_natural_question,
    profile_completion,
    profile_is_ready,
)
from state import (
    build_persisted_snapshot as _build_persisted_snapshot,
    clear_persistent_state as _clear_persistent_state,
    deserialize_transactions,
    empty_transactions,
    load_persistent_state as _load_persistent_state,
    normalize_transactions,
    save_persistent_state as _save_persistent_state,
)
from context_builder import build_context, build_llm_messages, build_recent_messages
from llm import check_ollama_health
from response_processing import (
    build_consultant_welcome,
)
import state as state_module
from ui_auth import handle_auth_gate
from ui_chat import process_user_turn, render_chat_history_and_feedback
from ui_profile import render_profile_dashboard_and_tools, render_profile_intake_gate

load_dotenv(override=True)

# Keep these names available from app module for test compatibility.
_ = (
    apply_profile_form_submission,
    build_context,
    build_llm_messages,
    build_recent_messages,
    extract_profile_updates,
    format_goal_timeline,
    format_profile_summary,
    format_update_fields,
    goal_progress,
    next_natural_question,
    normalize_transactions,
    profile_completion,
)

logger = logging.getLogger("pluto_app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


@st.cache_data
def load_products() -> list[dict[str, Any]]:
    file_path = DATA_DIR / "produtos_financeiros.json"
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_history() -> pd.DataFrame:
    file_path = DATA_DIR / "historico_atendimento.csv"
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


@st.cache_data
def load_tax_knowledge_data() -> dict[str, Any]:
    return load_tax_knowledge(BASE_DIR)


@st.cache_data
def extract_system_prompt() -> str:
    prompt_file = DOCS_DIR / "03-prompts.md"
    if not prompt_file.exists():
        return (
            "You are Pluto, a safe and educational financial assistant. "
            "Use only provided data, never invent assets, and always include risk warnings."
        )

    text = prompt_file.read_text(encoding="utf-8")
    marker = "## System Prompt"
    if marker not in text:
        return (
            "You are Pluto, a safe and educational financial assistant. "
            "Use only provided data and be prudent."
        )

    after = text.split(marker, 1)[1]
    match = re.search(r"```\s*(.*?)```", after, re.S)
    if not match:
        return (
            "You are Pluto, a safe and educational financial assistant. "
            "Use only provided data and be prudent."
        )

    return match.group(1).strip()


def get_texts(language: str) -> dict[str, Any]:
    return TEXTS.get(language, TEXTS["en"])


def _sync_state_module_paths() -> None:
    # Keep app-level monkeypatch compatibility for tests and local overrides.
    state_module.RUNTIME_DIR = RUNTIME_DIR
    state_module.STATE_FILE = STATE_FILE


def load_persistent_state(
    user_id: str | None = None, access_token: str | None = None
) -> dict[str, Any]:
    _sync_state_module_paths()
    return _load_persistent_state(user_id, access_token)


def save_persistent_state(
    state: dict[str, Any], user_id: str | None = None, access_token: str | None = None
) -> bool:
    _sync_state_module_paths()
    return _save_persistent_state(state, user_id, access_token)


def clear_persistent_state(
    user_id: str | None = None, access_token: str | None = None
) -> bool:
    _sync_state_module_paths()
    return _clear_persistent_state(user_id, access_token)


def build_persisted_snapshot(session_state: Any) -> dict[str, Any]:
    return _build_persisted_snapshot(session_state)


def log_event(event_name: str, payload: dict[str, Any] | None = None) -> None:
    """Log an event to the event log file."""
    event_payload = payload or {}
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "event": event_name,
        "payload": event_payload,
    }
    try:
        with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Failed to write event log: %s", exc)


def render_developer_modal(texts: dict[str, Any]) -> None:
    @st.dialog(texts["developer_modal_title"])
    def _developer_dialog() -> None:
        st.write(texts["developer_bio"])
        st.markdown(f"**{texts['developer_contacts']}**")
        st.markdown(
            f"- {texts['developer_email_label']}: [uilliambruno@gmail.com](mailto:uilliambruno@gmail.com)"
        )
        st.markdown(
            f"- {texts['developer_phone_label']}: [+971 058 564 5920](https://wa.me/971585645920)"
        )
        st.markdown(
            (
                f"- {texts['developer_linkedin_label']}: "
                "[linkedin.com/in/uilliam-santos-2206b8375]"
                "(https://www.linkedin.com/in/uilliam-santos-2206b8375/)"
            )
        )

    if st.button(texts["developer_link"], key="btn_developer_info"):
        _developer_dialog()


def main() -> None:
    st.set_page_config(page_title="Pluto Finance AI", page_icon="🪐", layout="wide")
    st.markdown(
        """
        <style>
            .block-container {padding-top: 1.2rem; max-width: 96vw !important; width: 96vw !important;}
            .stChatFloatingInputContainer {bottom: 1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(HIDE_STREAMLIT_CHROME, unsafe_allow_html=True)

    auth_user_id, auth_access_token = handle_auth_gate()

    if "state_loaded" not in st.session_state:
        st.session_state.state_loaded = False

    if "state_loaded_for_user" not in st.session_state:
        st.session_state.state_loaded_for_user = ""

    current_state_user = auth_user_id or "local"
    if st.session_state.state_loaded_for_user != current_state_user:
        st.session_state.state_loaded = False

    if not st.session_state.state_loaded:
        persisted = load_persistent_state(auth_user_id, auth_access_token)
        if persisted:
            try:
                st.session_state.language = "en"
                st.session_state.chat_mode = persisted.get("chat_mode", "guided")
                st.session_state.user_profile = persisted.get(
                    "user_profile", default_user_profile()
                )
                st.session_state.messages = persisted.get("messages", [])
                st.session_state.user_transactions = deserialize_transactions(
                    persisted.get("user_transactions", [])
                )
                st.session_state.rate_limit_notice = ""
                st.session_state.feedback = {}
                st.session_state.feedback_notice = ""
                st.session_state.state_restore_notice = "ok"
                st.session_state.profile_ready = profile_is_ready(
                    st.session_state.user_profile
                )
                log_event(
                    "state_restored", {"messages": len(st.session_state.messages)}
                )
            except Exception:
                st.session_state.state_restore_notice = "error"
                log_event("state_restore_error")
        else:
            st.session_state.user_profile = default_user_profile()
            st.session_state.messages = []
            st.session_state.user_transactions = empty_transactions()
            st.session_state.rate_limit_notice = ""
            st.session_state.feedback = {}
            st.session_state.feedback_notice = ""
            st.session_state.profile_ready = False
        st.session_state.state_loaded = True
        st.session_state.state_loaded_for_user = current_state_user

    if "language" not in st.session_state:
        st.session_state.language = "en"
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "guided"
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = default_user_profile()
    if "user_transactions" not in st.session_state:
        st.session_state.user_transactions = empty_transactions()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "rate_limit_notice" not in st.session_state:
        st.session_state.rate_limit_notice = ""
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}
    if "feedback_notice" not in st.session_state:
        st.session_state.feedback_notice = ""
    if "state_restore_notice" not in st.session_state:
        st.session_state.state_restore_notice = ""
    if "profile_ready" not in st.session_state:
        st.session_state.profile_ready = profile_is_ready(st.session_state.user_profile)
    if "llm_debug_status" not in st.session_state:
        st.session_state.llm_debug_status = ""

    language = "en"
    st.session_state.language = language
    texts = get_texts(language)

    title_col, auth_col = st.columns([5, 2])
    with title_col:
        st.title("🪐 Pluto Finance AI")
    with auth_col:
        if auth_user_id:
            user_email = str((st.session_state.auth_user or {}).get("email", ""))
            st.caption(user_email)
            action_col1, action_col2 = st.columns(2)
            with action_col1:
                clear_clicked = st.button(
                    texts["clear_data_button"],
                    use_container_width=True,
                    key="btn_clear_user_data",
                )
            with action_col2:
                logout_clicked = st.button(
                    texts["logout_button"],
                    use_container_width=True,
                    key="btn_logout",
                )

            if clear_clicked:
                cleared = clear_persistent_state(auth_user_id, auth_access_token)
                if cleared:
                    st.session_state.user_profile = default_user_profile()
                    st.session_state.user_transactions = empty_transactions()
                    st.session_state.messages = []
                    st.session_state.profile_ready = False
                    st.session_state.feedback = {}
                    st.session_state.feedback_notice = ""
                    st.session_state.rate_limit_notice = ""
                    st.session_state.state_loaded = False
                    st.success(texts["clear_data_success"])
                    st.rerun()
                else:
                    st.error(texts["clear_data_error"])

            if logout_clicked:
                st.session_state.auth_user = None
                st.session_state.login_email = ""
                st.session_state.state_loaded = False
                st.session_state.state_loaded_for_user = ""
                st.session_state.user_profile = default_user_profile()
                st.session_state.user_transactions = empty_transactions()
                st.session_state.messages = []
                st.session_state.profile_ready = False
                st.rerun()

    st.caption(texts["caption"])
    render_developer_modal(texts)
    unified_notice = " ".join(
        [
            texts["prototype_notice"],
            texts["prototype_legal_notice"],
            texts["brazil_focus_notice"],
        ]
    )
    st.info(unified_notice)

    if st.session_state.state_restore_notice == "ok":
        st.success(texts["state_restored"])
        st.session_state.state_restore_notice = ""
    elif st.session_state.state_restore_notice == "error":
        st.warning(texts["state_restore_error"])
        st.session_state.state_restore_notice = ""

    products = load_products()
    history = load_history()
    tax_knowledge = load_tax_knowledge_data()
    system_prompt = extract_system_prompt()
    ollama_ready = check_ollama_health()

    render_profile_intake_gate(
        texts=texts,
        language=language,
        auth_user_id=auth_user_id,
        auth_access_token=auth_access_token,
        log_event_fn=log_event,
        save_persistent_state_fn=save_persistent_state,
        build_persisted_snapshot_fn=build_persisted_snapshot,
        build_consultant_welcome_fn=build_consultant_welcome,
    )

    render_profile_dashboard_and_tools(
        texts=texts,
        language=language,
        auth_user_id=auth_user_id,
        auth_access_token=auth_access_token,
        log_event_fn=log_event,
        save_persistent_state_fn=save_persistent_state,
        build_persisted_snapshot_fn=build_persisted_snapshot,
        build_consultant_welcome_fn=build_consultant_welcome,
    )

    render_chat_history_and_feedback(
        texts=texts,
        auth_user_id=auth_user_id,
        auth_access_token=auth_access_token,
        log_event_fn=log_event,
        save_persistent_state_fn=save_persistent_state,
        build_persisted_snapshot_fn=build_persisted_snapshot,
    )

    process_user_turn(
        texts=texts,
        language=language,
        products=products,
        history=history,
        tax_knowledge=tax_knowledge,
        system_prompt=system_prompt,
        ollama_ready=ollama_ready,
        auth_user_id=auth_user_id,
        auth_access_token=auth_access_token,
        log_event_fn=log_event,
        save_persistent_state_fn=save_persistent_state,
        build_persisted_snapshot_fn=build_persisted_snapshot,
    )


if __name__ == "__main__":
    main()
