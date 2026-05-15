"""Authentication module for Supabase passwordless login."""

from __future__ import annotations

from typing import Any

import requests

from config import (
    SUPABASE_EMAIL_REDIRECT_TO,
    SUPABASE_URL,
)
from state import supabase_enabled, supabase_headers


def send_login_otp(email: str) -> tuple[bool, str]:
    """Send a one-time password via email for login."""
    if not supabase_enabled():
        return False, "Supabase is not configured in this environment."

    payload = {
        "email": email.strip().lower(),
        "create_user": True,
    }
    if SUPABASE_EMAIL_REDIRECT_TO:
        payload["email_redirect_to"] = SUPABASE_EMAIL_REDIRECT_TO
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/otp",
            headers=supabase_headers(),
            json=payload,
            timeout=20,
        )
    except requests.RequestException:
        return False, "I could not connect to the login service right now."

    if response.status_code in {200, 201}:
        return True, ""

    try:
        error_message = response.json().get("msg") or response.json().get("error")
    except ValueError:
        error_message = response.text

    error_text = str(error_message or "").lower()
    if "rate" in error_text and "limit" in error_text:
        return (
            False,
            "Too many attempts in a short time. Wait about 60 seconds and use the latest code received.",
        )

    return False, str(error_message or "Failed to send login code by email.")


def parse_auth_success_response(
    data: dict[str, Any], fallback_email: str = ""
) -> tuple[dict[str, Any] | None, str]:
    """Extract user info and token from successful auth response."""
    user = data.get("user") or {}
    access_token = data.get("access_token")
    if not user.get("id") or not access_token:
        return None, "Incomplete login session returned by the provider."

    return {
        "user_id": str(user.get("id")),
        "email": str(user.get("email") or fallback_email.strip().lower()),
        "access_token": str(access_token),
    }, ""


def verify_login_otp(email: str, otp_code: str) -> tuple[dict[str, Any] | None, str]:
    """Verify a one-time password and return auth credentials."""
    if not supabase_enabled():
        return None, "Supabase is not configured in this environment."

    payload = {
        "email": email.strip().lower(),
        "token": otp_code.strip(),
        "type": "email",
    }
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/verify",
            headers=supabase_headers(),
            json=payload,
            timeout=20,
        )
    except requests.RequestException:
        return None, "I could not validate the code right now."

    if response.status_code not in {200, 201}:
        try:
            data = response.json()
            message = (
                data.get("msg") or data.get("error_description") or data.get("error")
            )
        except ValueError:
            message = response.text
        return None, str(message or "Invalid or expired code.")

    try:
        data = response.json()
    except ValueError:
        return None, "Invalid response from the authentication service."

    return parse_auth_success_response(data, fallback_email=email)


def verify_magic_link_token(token_hash: str) -> tuple[dict[str, Any] | None, str]:
    """Verify a magic link token from email."""
    if not supabase_enabled():
        return None, "Supabase is not configured in this environment."

    payload = {
        "token_hash": token_hash.strip(),
        "type": "email",
    }
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/verify",
            headers=supabase_headers(),
            json=payload,
            timeout=20,
        )
    except requests.RequestException:
        return None, "I could not validate the magic link right now."

    if response.status_code not in {200, 201}:
        try:
            data = response.json()
            message = (
                data.get("msg") or data.get("error_description") or data.get("error")
            )
        except ValueError:
            message = response.text
        return None, str(message or "Invalid or expired login link.")

    try:
        data = response.json()
    except ValueError:
        return None, "Invalid response from the authentication service."

    return parse_auth_success_response(data)
