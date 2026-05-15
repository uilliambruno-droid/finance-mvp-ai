"""Profile management module for user financial profiles."""

from __future__ import annotations

import re
from typing import Any

from config import get_texts
from finance_knowledge import extract_user_name


def default_user_profile() -> dict[str, Any]:
    """Create a default empty user profile."""
    return {
        "nome": "",
        "renda_mensal": None,
        "fonte_renda": "",
        "sem_renda": False,
        "desempregado": False,
        "perfil_investidor": "",
        "aceita_risco": None,
        "patrimonio_atual": None,
        "meta_patrimonial": None,
        "prazo_meta_meses": None,
        "gastos_mensais": None,
        "tem_gastos": None,
        "perfil_pronto": False,
        "observacoes": "",
    }


def profile_is_ready(profile: dict[str, Any]) -> bool:
    """Check if a profile has the minimum required fields filled in."""
    has_income = profile.get("renda_mensal") not in (None, "") or profile.get(
        "sem_renda"
    )
    return bool(
        profile.get("nome")
        and has_income
        and profile.get("perfil_investidor")
        and profile.get("perfil_pronto")
    )


def apply_profile_form_submission(
    *,
    name: str,
    income: float | None,
    income_source: str,
    investor_style: str,
    spending: float | None,
    has_spending: bool,
    current_wealth: float | None,
    target_wealth: float | None,
    target_deadline_months: int | None,
    notes: str,
) -> dict[str, Any]:
    """Create a profile from form submission data."""
    profile = default_user_profile()
    profile["nome"] = name.strip().title()
    profile["renda_mensal"] = income
    profile["sem_renda"] = income in (None, 0)
    profile["desempregado"] = income in (None, 0) and not income_source.strip()
    profile["fonte_renda"] = income_source.strip()
    profile["perfil_investidor"] = investor_style
    profile["aceita_risco"] = investor_style != "Conservative"
    profile["gastos_mensais"] = spending
    profile["tem_gastos"] = has_spending
    profile["patrimonio_atual"] = current_wealth
    profile["meta_patrimonial"] = target_wealth
    profile["prazo_meta_meses"] = target_deadline_months
    profile["observacoes"] = notes.strip()
    profile["perfil_pronto"] = True
    return profile


def goal_progress(profile: dict[str, Any]) -> tuple[float | None, float | None, int]:
    """Calculate goal progress as (current, target, percentage)."""
    current = profile.get("patrimonio_atual")
    target = profile.get("meta_patrimonial")
    if current in (None, "") or target in (None, ""):
        return None, None, 0
    current_value = float(current)
    target_value = float(target)
    if target_value <= 0:
        return current_value, target_value, 0
    progress = int(min(100, max(0, round((current_value / target_value) * 100))))
    return current_value, target_value, progress


def format_goal_timeline(months: int | None, language: str) -> str:
    """Format a deadline in months to a human-readable string."""
    if not months or months <= 0:
        return "—"
    if months < 24:
        return f"{months} months"
    years = months / 12
    years_label = f"{years:.1f}" if years % 1 else f"{int(years)}"
    return f"{years_label} years ({months} months)"


def profile_completion(profile: dict[str, Any]) -> int:
    """Return profile completion as a percentage (0-100)."""
    score = 0
    if profile.get("fonte_renda") or profile.get("sem_renda"):
        score += 1
    if profile.get("renda_mensal") not in (None, "") or profile.get("sem_renda"):
        score += 1
    if profile.get("perfil_investidor"):
        score += 1
    if profile.get("patrimonio_atual") not in (None, ""):
        score += 1
    if profile.get("meta_patrimonial") not in (None, ""):
        score += 1
    if profile.get("prazo_meta_meses") not in (None, ""):
        score += 1
    return int((score / 6) * 100)


def format_profile_summary(profile: dict[str, Any], language: str) -> str:
    """Format profile fields as a summary string."""
    labels = {
        "nome": "Name",
        "fonte_renda": "Source",
        "renda_mensal": "Income",
        "sem_renda": "Status",
        "perfil_investidor": "Profile",
        "patrimonio_atual": "Net worth",
        "meta_patrimonial": "Target",
        "prazo_meta_meses": "Deadline",
    }

    parts = []
    for key in [
        "nome",
        "fonte_renda",
        "renda_mensal",
        "sem_renda",
        "perfil_investidor",
        "patrimonio_atual",
        "meta_patrimonial",
        "prazo_meta_meses",
    ]:
        value = profile.get(key)
        if value in (None, "", []):
            continue
        label = labels[key]
        if key == "renda_mensal":
            parts.append(f"{label}: {value:,.2f}")
        elif key in {"patrimonio_atual", "meta_patrimonial"}:
            parts.append(f"{label}: {float(value):,.2f}")
        elif key == "prazo_meta_meses":
            parts.append(f"{label}: {format_goal_timeline(int(value), language)}")
        elif key == "sem_renda" and value:
            parts.append(f"{label}: no income")
        elif key != "sem_renda":
            parts.append(f"{label}: {value}")
    return " • ".join(parts)


def extract_profile_updates(user_text: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Extract profile field updates from user message."""
    updates: dict[str, Any] = {}
    text = user_text.strip()
    lower = text.lower()

    user_name = extract_user_name(text)
    if user_name and not profile.get("nome"):
        updates["nome"] = user_name

    income_match = re.search(
        r"(?:monthly income|i make|salary|income)\D*(\d+[\d\.,]*)",
        lower,
    )
    if income_match:
        income_raw = income_match.group(1).replace(".", "").replace(",", ".")
        try:
            updates["renda_mensal"] = float(income_raw)
            updates["sem_renda"] = False
            if not profile.get("fonte_renda"):
                updates["fonte_renda"] = "salary"
        except ValueError:
            pass

    if any(
        term in lower
        for term in [
            "unemployed",
            "out of work",
        ]
    ):
        updates["desempregado"] = True
        updates["sem_renda"] = True
        updates["renda_mensal"] = 0.0
        updates["fonte_renda"] = "no income"

    if any(term in lower for term in ["no income", "without income"]):
        updates["sem_renda"] = True
        updates["renda_mensal"] = 0.0
        if not updates.get("fonte_renda"):
            updates["fonte_renda"] = "no income"

    if any(term in lower for term in ["salary"]):
        updates["fonte_renda"] = "salary"
    elif any(term in lower for term in ["freela", "freelance", "freelas"]):
        updates["fonte_renda"] = "freelance"
    elif any(term in lower for term in ["business", "own business"]):
        updates["fonte_renda"] = "own business"

    if any(term in lower for term in ["conservative", "low risk"]):
        updates["perfil_investidor"] = "Conservative"
        updates["aceita_risco"] = False
    elif any(term in lower for term in ["moderate"]):
        updates["perfil_investidor"] = "Moderate"
        updates["aceita_risco"] = True
    elif any(term in lower for term in ["aggressive", "high risk"]):
        updates["perfil_investidor"] = "Aggressive"
        updates["aceita_risco"] = True

    return updates


def format_update_fields(profile_updates: dict[str, Any], language: str) -> str:
    """Format profile update fields as a comma-separated list."""
    labels = {
        "nome": "name",
        "renda_mensal": "income",
        "fonte_renda": "income source",
        "sem_renda": "income status",
        "desempregado": "work status",
        "perfil_investidor": "profile",
        "patrimonio_atual": "net worth",
        "meta_patrimonial": "target",
        "prazo_meta_meses": "target deadline",
    }
    return ", ".join(labels.get(key, key) for key in profile_updates.keys())


def next_natural_question(
    profile: dict[str, Any], language: str, has_transactions: bool, chat_mode: str
) -> str:
    """Return a context-aware follow-up question in guided chat mode.

    Only fires when the profile is ready (intake form completed) and the chat
    mode is ``"guided"``.  For quick mode or incomplete profiles this always
    returns an empty string so the LLM answer is not disrupted.

    Uses shared text resources from config.
    """
    if chat_mode != "guided":
        return ""
    if not profile_is_ready(profile):
        return ""

    texts = get_texts(language)

    if not profile.get("fonte_renda") and not profile.get("sem_renda"):
        return texts["followup_income_source"]

    if not has_transactions:
        return texts["followup_csv"]

    return texts["followup_goal"]
