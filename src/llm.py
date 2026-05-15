"""LLM (Large Language Model) API integration module."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_MAX_RETRIES,
    OPENROUTER_MODEL,
    OPENROUTER_RETRY_BASE_SECONDS,
    OPENROUTER_TIMEOUT_SECONDS,
    OPENROUTER_URL,
    LLM_MAX_OUTPUT_TOKENS,
)

logger = logging.getLogger("pluto_app")


def log_event(event_name: str, payload: dict[str, Any] | None = None) -> None:
    """Log an event (imported from app module, but defined here for reference)."""
    # This function is actually in app.py - we import it from there
    pass


def call_openrouter(messages: list[dict[str, str]]) -> tuple[str | None, bool, str]:
    """Call OpenRouter API with retry logic and rate limit detection."""
    api_key = OPENROUTER_API_KEY.strip()
    if not api_key or api_key.lower().startswith("your_"):
        return None, False, "OpenRouter has no API key configured."

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": LLM_MAX_OUTPUT_TOKENS,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    retriable_statuses = {429, 500, 502, 503, 504}

    for attempt in range(OPENROUTER_MAX_RETRIES + 1):
        try:
            # log_event would be called here
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=OPENROUTER_TIMEOUT_SECONDS,
            )

            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    return (
                        None,
                        False,
                        "OpenRouter returned 200 with no usable content.",
                    )

                answer = str(choices[0].get("message", {}).get("content", "")).strip()
                return (answer if answer else None), False, "OpenRouter returned 200."

            try:
                data = response.json()
                error_message = data.get("error", {}).get("message", "")
            except ValueError:
                error_message = response.text

            lower_error = str(error_message).lower()
            rate_limit_hit = response.status_code == 429 or any(
                marker in lower_error
                for marker in ["rate", "quota", "limit", "429", "credits"]
            )

            if (
                response.status_code in retriable_statuses
                and attempt < OPENROUTER_MAX_RETRIES
            ):
                backoff = OPENROUTER_RETRY_BASE_SECONDS * (2**attempt)
                time.sleep(backoff)
                continue

            return (
                None,
                rate_limit_hit,
                f"OpenRouter returned {response.status_code}: {str(error_message)[:120]}",
            )

        except (requests.RequestException, ValueError, KeyError, IndexError):
            if attempt < OPENROUTER_MAX_RETRIES:
                backoff = OPENROUTER_RETRY_BASE_SECONDS * (2**attempt)
                time.sleep(backoff)
                continue
            return (
                None,
                False,
                "OpenRouter failed before returning a valid response.",
            )

    return None, False, "OpenRouter unavailable after retry attempts."


def call_primary_llm(
    messages: list[dict[str, str]],
) -> tuple[str | None, bool, str, str]:
    """Call the primary LLM (OpenRouter) and return answer, rate limit status, debug message, and provider."""
    answer, rate_limit_hit, debug_message = call_openrouter(messages)
    return answer, rate_limit_hit, debug_message, "openrouter"


def call_ollama(messages: list[dict[str, str]]) -> str | None:
    """Call local Ollama model as a fallback."""
    payload = {"model": OLLAMA_MODEL, "stream": False, "messages": messages}
    try:
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=90)
        if response.status_code != 200:
            return None
        data = response.json()
        content = data.get("message", {}).get("content")
        return str(content) if content else None
    except requests.RequestException:
        return None


def check_ollama_health() -> bool:
    """Check if Ollama service is available and healthy."""
    disable_ollama = os.getenv("DISABLE_OLLAMA", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if disable_ollama:
        return False

    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    if environment == "production" and "localhost" in OLLAMA_URL.lower():
        return False

    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).status_code == 200
    except requests.RequestException:
        return False
