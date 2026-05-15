"""State persistence module for user data storage."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# These will be imported from config
from config import (
    RUNTIME_DIR,
    STATE_FILE,
    SUPABASE_ANON_KEY,
    SUPABASE_URL,
    SUPABASE_USER_STATES_TABLE,
)

logger = logging.getLogger("pluto_app")


def empty_transactions() -> pd.DataFrame:
    """Create an empty transactions DataFrame."""
    return pd.DataFrame(columns=["data", "valor", "categoria", "tipo"])


def serialize_transactions(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert transactions DataFrame to list of dicts for JSON storage."""
    if dataframe.empty:
        return []
    copy = dataframe.copy()
    copy["data"] = copy["data"].astype(str)
    return copy.to_dict(orient="records")


def deserialize_transactions(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert list of transaction dicts back to DataFrame."""
    if not records:
        return empty_transactions()
    dataframe = pd.DataFrame(records)
    return normalize_transactions(dataframe)


def normalize_transactions(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize transaction columns and data types."""
    if dataframe.empty:
        return empty_transactions()

    column_map = {
        "date": "data",
        "data": "data",
        "amount": "valor",
        "valor": "valor",
        "category": "categoria",
        "categoria": "categoria",
        "type": "tipo",
        "tipo": "tipo",
    }
    renamed = dataframe.rename(
        columns={
            column: column_map.get(column.lower(), column)
            for column in dataframe.columns
        }
    )

    for column in ["data", "valor", "categoria", "tipo"]:
        if column not in renamed.columns:
            renamed[column] = None

    renamed = renamed[["data", "valor", "categoria", "tipo"]].copy()
    renamed["data"] = pd.to_datetime(renamed["data"], errors="coerce")
    renamed["valor"] = pd.to_numeric(renamed["valor"], errors="coerce").fillna(0.0)
    renamed["categoria"] = renamed["categoria"].fillna("geral").astype(str)
    renamed["tipo"] = renamed["tipo"].fillna("saida").astype(str).str.lower()
    renamed.loc[~renamed["tipo"].isin(["saida", "entrada"]), "tipo"] = "saida"
    return renamed


def user_state_file(user_id: str) -> Path:
    """Get the file path for a user's state file."""
    digest = hashlib.sha256(user_id.strip().lower().encode("utf-8")).hexdigest()
    return RUNTIME_DIR / "users" / f"{digest}.json"


def supabase_enabled() -> bool:
    """Check if Supabase is configured."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def supabase_headers(access_token: str | None = None) -> dict[str, str]:
    """Build HTTP headers for Supabase API requests."""
    token = access_token or SUPABASE_ANON_KEY
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def load_persistent_state(
    user_id: str | None = None, access_token: str | None = None
) -> dict[str, Any]:
    """Load user state from Supabase or local file."""
    if supabase_enabled() and user_id and access_token:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_USER_STATES_TABLE}",
                headers=supabase_headers(access_token),
                params={"select": "state", "user_id": f"eq.{user_id}", "limit": 1},
                timeout=20,
            )
            if response.status_code != 200:
                return {}
            records = response.json()
            if not isinstance(records, list) or not records:
                return {}
            state = records[0].get("state", {})
            return state if isinstance(state, dict) else {}
        except (requests.RequestException, ValueError):
            return {}

    if user_id:
        state_file = user_state_file(user_id)
        if not state_file.exists():
            return {}
        try:
            with open(state_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}

    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def save_persistent_state(
    state: dict[str, Any], user_id: str | None = None, access_token: str | None = None
) -> bool:
    """Save user state to Supabase or local file."""
    if supabase_enabled() and user_id and access_token:
        payload = [
            {
                "user_id": user_id,
                "state": state,
                "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            }
        ]
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_USER_STATES_TABLE}",
                headers={
                    **supabase_headers(access_token),
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=payload,
                timeout=20,
            )
            return response.status_code in {200, 201}
        except requests.RequestException:
            return False

    if user_id:
        try:
            state_file = user_state_file(user_id)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False, indent=2)
            return True
        except OSError as exc:
            logger.warning("Failed to save user persistent state: %s", exc)
            return False

    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        logger.warning("Failed to save persistent state: %s", exc)
        return False


def clear_persistent_state(
    user_id: str | None = None, access_token: str | None = None
) -> bool:
    """Delete user state from Supabase or local file."""
    if supabase_enabled() and user_id and access_token:
        try:
            response = requests.delete(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_USER_STATES_TABLE}",
                headers={**supabase_headers(access_token), "Prefer": "return=minimal"},
                params={"user_id": f"eq.{user_id}"},
                timeout=20,
            )
            return response.status_code in {200, 204}
        except requests.RequestException:
            return False

    if user_id:
        state_file = user_state_file(user_id)
        if not state_file.exists():
            return True
        try:
            state_file.unlink()
            return True
        except OSError:
            return False

    if not STATE_FILE.exists():
        return True
    try:
        STATE_FILE.unlink()
        return True
    except OSError:
        return False


def build_persisted_snapshot(session_state: Any) -> dict[str, Any]:
    """Create a snapshot of session state for persistence."""
    messages = [
        {
            "role": str(message.get("role", "")),
            "content": str(message.get("content", "")),
        }
        for message in session_state.messages[-30:]
        if message.get("role") in {"assistant", "user"}
    ]
    return {
        "language": session_state.language,
        "chat_mode": session_state.chat_mode,
        "user_profile": session_state.user_profile,
        "messages": messages,
        "user_transactions": serialize_transactions(session_state.user_transactions),
    }
