"""Assistant response post-processing and safeguards."""

from __future__ import annotations

from typing import Any

from config import get_texts
from profile import format_update_fields


def fallback_offline_response(user_text: str, language: str) -> str:
    texts = get_texts(language)
    lower = user_text.lower().strip()
    if any(
        phrase in lower
        for phrase in [
            "hello",
            "hi",
            "how are you",
        ]
    ):
        return texts["fallback_greeting"]
    return texts["fallback_general"]


def normalize_assistant_text(text: str) -> str:
    return text


def _looks_like_portuguese(text: str) -> bool:
    lower = text.lower()
    hints = [
        " voce ",
        " você ",
        " seu ",
        " sua ",
        " para ",
        " com ",
        " hoje",
        " vamos ",
        " patrimonio",
        " patrimônio",
        " gasto",
        " ganhos",
        " renda",
    ]
    padded = f" {lower} "
    return sum(1 for hint in hints if hint in padded) >= 2


def enforce_response_language(answer: str, language: str) -> str:
    if language != "en":
        return answer

    if _looks_like_portuguese(answer):
        return (
            "Quick correction: I'll keep replies in English from now on.\n\n"
            "I can help you reduce expenses, plan monthly spending, and update your "
            "financial status from exact values you share in chat."
        )

    return answer


def contains_sensitive_offtopic_content(user_text: str) -> bool:
    lower = user_text.lower()
    sensitive_terms = [
        "sexual",
        "porn",
        "nude",
        "escort",
        "fuck",
        "shit",
        "bitch",
        "asshole",
    ]
    return any(term in lower for term in sensitive_terms)


def build_consultant_welcome(profile: dict[str, Any], language: str) -> str:
    """Build a personalised welcome that acknowledges the user's profile."""
    name = profile.get("nome", "")
    investor = profile.get("perfil_investidor", "")
    renda = profile.get("renda_mensal")
    sem_renda = profile.get("sem_renda", False)

    greeting = f"Hey {name}! " if name else "Hey! "
    lines = [
        greeting
        + "Your profile is set. I'm ready to act as your personal financial consultant - no fluff."
    ]
    if investor:
        lines.append(
            f"Investor style noted: **{investor}**. I'll calibrate my recommendations accordingly."
        )
    if sem_renda:
        lines.append(
            "I see you're not relying on income right now - I'll prioritize stability and practical next steps."
        )
    elif renda:
        lines.append(f"With **R$ {renda:,.0f}/mo** on hand, let's make the most of it.")
    lines.append("What do you want to tackle first?")
    return "\n\n".join(lines)


def safe_financial_redirect(language: str) -> str:
    return (
        "I can help with financial planning, spending, income, and investments. "
        "If you want, tell me your monthly income, expenses, or goal and I'll keep it practical."
    )


def apply_post_response_validation(
    response_text: str,
    profile: dict[str, Any],
    user_text: str,
    unknown_assets: list[str],
    language: str,
    rate_limit_hit: bool = False,
    profile_updates: dict[str, Any] | None = None,
) -> str:
    texts = get_texts(language)
    lower = user_text.lower()
    answer = (response_text or "").strip()

    # Defensive cleanup for providers returning literal "None" as text content.
    if answer.lower() == "none":
        answer = ""

    if contains_sensitive_offtopic_content(user_text):
        return safe_financial_redirect(language)

    if not answer:
        answer = fallback_offline_response(user_text, language)

    if len(answer) < 20:
        answer = (answer + texts["short_answer"]).strip()

    if profile_updates:
        fields = format_update_fields(profile_updates, language)
        answer = texts["updated_profile"].format(fields=fields) + "\n\n" + answer

    if profile.get("desempregado") or profile.get("sem_renda"):
        if any(
            term in lower
            for term in [
                "unemployed",
                "no income",
            ]
        ):
            answer += "\n\n" + texts["unemployment_support"]
            answer += "\n\n" + texts["no_income_prompt"]

    if unknown_assets:
        unknown_str = ", ".join(unknown_assets)
        answer += "\n\n" + texts["unknown_assets"].format(assets=unknown_str)

    if rate_limit_hit:
        answer += "\n\n" + texts["rate_limit_notice"]

    return answer
