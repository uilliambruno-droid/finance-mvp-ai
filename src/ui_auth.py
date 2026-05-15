"""Authentication UI flow for Streamlit."""

from __future__ import annotations

import time

import streamlit as st

from auth import send_login_otp, verify_login_otp, verify_magic_link_token
from config import AUTH_REQUIRED, EMAIL_LOGIN_REQUIRED, OTP_COOLDOWN_SECONDS, get_texts
from state import supabase_enabled


def _ensure_auth_session_defaults() -> None:
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None
    if "login_email" not in st.session_state:
        st.session_state.login_email = ""
    if "login_language" not in st.session_state:
        st.session_state.login_language = "en"
    if "login_last_otp_sent_at" not in st.session_state:
        st.session_state.login_last_otp_sent_at = 0.0


def _get_auth_tokens() -> tuple[str | None, str | None]:
    auth_user_id: str | None = None
    auth_access_token: str | None = None
    auth_user = st.session_state.auth_user
    if auth_user:
        auth_user_id = str(auth_user.get("user_id", "")).strip() or None
        auth_access_token = str(auth_user.get("access_token", "")).strip() or None
    return auth_user_id, auth_access_token


def handle_auth_gate() -> tuple[str | None, str | None]:
    """Render auth screens and stop execution until authenticated when needed."""
    _ensure_auth_session_defaults()
    auth_user_id, auth_access_token = _get_auth_tokens()

    if supabase_enabled() and AUTH_REQUIRED:
        if not auth_user_id or not auth_access_token:
            st.session_state.login_language = "en"
            login_texts = get_texts("en")

            st.title(login_texts["login_title"])
            st.caption(login_texts["login_caption"])

            query_params = st.query_params
            token_hash = str(query_params.get("token_hash", "")).strip()
            token_type = str(query_params.get("type", "")).strip().lower()
            token_key = f"{token_hash}:{token_type}"

            if "last_magic_link_token" not in st.session_state:
                st.session_state.last_magic_link_token = ""

            if (
                token_hash
                and token_type == "email"
                and st.session_state.last_magic_link_token != token_key
            ):
                auth_data, error_message = verify_magic_link_token(token_hash)
                st.session_state.last_magic_link_token = token_key
                if auth_data:
                    st.session_state.auth_user = auth_data
                    st.session_state.state_loaded = False
                    st.query_params.clear()
                    st.rerun()
                st.error(error_message)

            st.caption(login_texts["login_magic_link_hint"])

            with st.form("request_login_otp", clear_on_submit=False):
                email = st.text_input(
                    login_texts["login_email_label"],
                    value=st.session_state.login_email,
                    placeholder=login_texts["login_email_placeholder"],
                ).strip()
                request_otp = st.form_submit_button(
                    login_texts["login_send_code"], use_container_width=True
                )

            if request_otp:
                if not email or "@" not in email:
                    st.error(login_texts["login_invalid_email"])
                else:
                    now = time.time()
                    elapsed = now - float(st.session_state.login_last_otp_sent_at)
                    if elapsed < OTP_COOLDOWN_SECONDS:
                        remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
                        st.warning(
                            login_texts["login_wait_before_resend"].format(
                                seconds=remaining
                            )
                        )
                    else:
                        sent, error_message = send_login_otp(email)
                        if sent:
                            st.session_state.login_email = email.lower()
                            st.session_state.login_last_otp_sent_at = now
                            st.success(login_texts["login_code_sent"])
                        else:
                            st.error(error_message)

            if st.session_state.login_email:
                with st.form("verify_login_otp", clear_on_submit=True):
                    otp_code = st.text_input(
                        login_texts["login_otp_label"],
                        placeholder=login_texts["login_otp_placeholder"],
                    ).strip()
                    verify_otp = st.form_submit_button(
                        login_texts["login_submit"],
                        use_container_width=True,
                        type="primary",
                    )

                if verify_otp:
                    auth_data, error_message = verify_login_otp(
                        st.session_state.login_email, otp_code
                    )
                    if auth_data:
                        st.session_state.auth_user = auth_data
                        st.session_state.state_loaded = False
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(error_message)

            st.stop()

    if EMAIL_LOGIN_REQUIRED and not auth_user_id:
        st.session_state.login_language = "en"
        login_texts = get_texts("en")

        st.title(login_texts["login_title"])
        st.caption(login_texts["login_email_only_caption"])

        with st.form("email_only_login_form", clear_on_submit=False):
            email = st.text_input(
                login_texts["login_email_label"],
                value=st.session_state.login_email,
                placeholder=login_texts["login_email_placeholder"],
            ).strip()
            submit_email_login = st.form_submit_button(
                login_texts["login_continue"], use_container_width=True, type="primary"
            )

        if submit_email_login:
            if not email or "@" not in email:
                st.error(login_texts["login_invalid_email"])
            else:
                normalized_email = email.lower()
                st.session_state.login_email = normalized_email
                st.session_state.auth_user = {
                    "user_id": normalized_email,
                    "email": normalized_email,
                    "access_token": "",
                }
                st.session_state.state_loaded = False
                st.rerun()

        st.stop()

    if supabase_enabled() and not AUTH_REQUIRED and not EMAIL_LOGIN_REQUIRED:
        login_texts = get_texts(st.session_state.login_language)
        st.info(login_texts["login_bypass_notice"])

    return auth_user_id, auth_access_token
