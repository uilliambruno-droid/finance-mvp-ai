from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any


def load_tax_knowledge(base_dir: Path) -> dict[str, Any]:
    file_path = base_dir / "data" / "knowledge" / "tax_knowledge.json"
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def is_tax_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "ir",
        "darf",
        "iof",
        "tax",
        "taxation",
        "capital gain",
    ]
    return any(keyword in lower for keyword in keywords)


def is_portfolio_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "portfolio",
        "diversify",
        "allocate",
        "allocation",
    ]
    return any(keyword in lower for keyword in keywords)


def is_instrument_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "stock",
        "stocks",
        "etf",
        "treasury",
        "selic",
        "crypto",
        "bitcoin",
        "ethereum",
        "fixed income",
    ]
    return any(keyword in lower for keyword in keywords)


def _find_products_by_category(
    products: list[dict[str, Any]], categories: set[str]
) -> list[dict[str, Any]]:
    selected = []
    for item in products:
        category = str(item.get("categoria", "")).lower()
        if category in categories:
            selected.append(item)
    return selected


def build_portfolio_guidance(
    profile: dict[str, Any], products: list[dict[str, Any]], language: str
) -> str:
    investor_profile = str(profile.get("perfil_investidor", "")).lower()
    no_income = bool(profile.get("sem_renda") or profile.get("desempregado"))

    if no_income:
        return (
            "Portfolio guidance for this moment: prioritize financial stability first. "
            "Focus on essential spending, emergency cash, and income generation before taking market risk."
        )

    if investor_profile.startswith("conserv"):
        target_mix = "70% fixed income / 20% broad ETFs / 10% protection and cash"
        categories = {"renda_fixa", "etf", "fundo"}
    elif investor_profile.startswith("moder"):
        target_mix = (
            "50% fixed income / 35% global ETFs and stocks / 15% satellite positions"
        )
        categories = {"renda_fixa", "etf", "acao", "fundo"}
    else:
        target_mix = "30% fixed income / 50% ETFs and stocks / 20% satellite positions (including capped crypto)"
        categories = {"renda_fixa", "etf", "acao", "cripto", "fundo"}

    selected_products = _find_products_by_category(products, categories)[:6]
    names = [
        str(item.get("nome", "")) for item in selected_products if item.get("nome")
    ]

    lines = [f"Suggested educational allocation mix: {target_mix}."]
    if names:
        lines.append("Examples from current catalog: " + ", ".join(names) + ".")
    lines.append(
        "Use position sizing and diversification; avoid concentrating in one single asset."
    )
    return " ".join(lines)


def build_tax_guidance(tax_knowledge: dict[str, Any], language: str) -> str:
    if not tax_knowledge:
        return ""

    tax_br = tax_knowledge.get("taxacao_brasil", {})
    ir_table = tax_br.get("renda_fixa_regressiva_ir", [])

    parts = [
        "Taxation essentials:",
        "Brazilian fixed income often uses a regressive income tax schedule by holding period.",
        "Current scope is Brazil-first, so taxation guidance is focused on Brazilian rules.",
    ]
    if ir_table:
        parts.append("Reference brackets: " + " | ".join(ir_table) + ".")
    iof_text = str(tax_br.get("iof", ""))
    if iof_text:
        parts.append("IOF: " + iof_text)
    return " ".join(part for part in parts if part)


def build_instrument_guidance(tax_knowledge: dict[str, Any], language: str) -> str:
    if not tax_knowledge:
        return ""

    selic = tax_knowledge.get("selic", {})
    tesouro = tax_knowledge.get("tesouro_direto", {})

    parts = [
        "Key product notes:",
        str(selic.get("descricao", "")),
        str(selic.get("uso_pratico", "")),
        "Treasury Direct equivalents in Brazil include Selic, inflation-linked and fixed-rate government bonds.",
        str(tesouro.get("tesouro_selic", "")),
        str(tesouro.get("tesouro_ipca", "")),
        str(tesouro.get("tesouro_prefixado", "")),
    ]
    return " ".join(part for part in parts if part)


def build_finance_knowledge_context(
    user_text: str,
    profile: dict[str, Any],
    products: list[dict[str, Any]],
    tax_knowledge: dict[str, Any],
    language: str,
) -> str:
    sections: list[str] = []

    scenario = build_scenario_guidance(user_text, language)
    if scenario:
        sections.append(scenario)

    if is_instrument_query(user_text):
        instrument = build_instrument_guidance(tax_knowledge, language)
        if instrument:
            sections.append(instrument)

    if is_tax_query(user_text):
        tax = build_tax_guidance(tax_knowledge, language)
        if tax:
            sections.append(tax)

    if is_portfolio_query(user_text) or is_instrument_query(user_text):
        portfolio = build_portfolio_guidance(profile, products, language)
        if portfolio:
            sections.append(portfolio)

    legal_notice = str(tax_knowledge.get("aviso_legal", "")).strip()
    if legal_notice and sections:
        sections.append(legal_notice)

    return "\n\n".join(section for section in sections if section)


# ---------------------------------------------------------------------------
# Scenario-based guidance
# ---------------------------------------------------------------------------

SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "reserva_emergencia": [
        "emergency fund",
        "cash reserve",
    ],
    "dividas_vs_investir": [
        "debt",
        "loan",
        "pay off",
    ],
    "aportes_mensais": [
        "monthly contribution",
        "monthly investment",
        "contribute monthly",
    ],
    "aposentadoria": [
        "retire",
        "retirement",
        "long term",
    ],
    "etf_vs_renda_fixa": [
        "etf vs",
        "vs etf",
        "vs fixed income",
        "compare",
        "compare etf",
        "etf or fixed income",
    ],
}

SCENARIO_GUIDANCE: dict[str, dict[str, str]] = {
    "reserva_emergencia": {
        "en": (
            "**Emergency Fund — how to build it:**\n"
            "• Target: 6× monthly expenses in highly liquid assets (Tesouro Selic, daily-liquidity CDB).\n"
            "• For freelancers or variable income: aim for 9–12×.\n"
            "• Never use the emergency fund for risky investments — it's protection, not yield.\n"
            "• Only after the fund is built, allocate surplus to growth portfolios."
        ),
    },
    "dividas_vs_investir": {
        "en": (
            "**Debt vs. Invest — how to decide:**\n"
            "• If debt rate > expected investment return → pay off debt first.\n"
            "• Credit card/revolving debt (>12% p.m.): urgent payoff, no negotiation.\n"
            "• Mortgage (rate < Selic): investing in parallel may work.\n"
            "• Rule of thumb: pay off debts above CDI rate before investing in variable income."
        ),
    },
    "aportes_mensais": {
        "en": (
            "**Monthly Contributions — strategy:**\n"
            "• Use Dollar Cost Averaging (DCA): fixed contribution each month regardless of market.\n"
            "• Suggested split: 50% fixed income (Tesouro, CDB) + 30% ETFs + 20% flexible.\n"
            "• Automate contributions right after payday — pay yourself first.\n"
            "• Review allocation every 6–12 months as your profile evolves."
        ),
    },
    "aposentadoria": {
        "en": (
            "**Retirement / Financial Independence:**\n"
            "• 25× rule: accumulate 25× your annual expenses for financial independence.\n"
            "• Private pension (PGBL vs VGBL): PGBL for those using full tax deduction; VGBL for others.\n"
            "• Long horizon favors equities early, gradually shifting to fixed income as you near the goal.\n"
            "• Consider Tesouro IPCA+ as a long-term anchor to protect purchasing power."
        ),
    },
    "etf_vs_renda_fixa": {
        "en": (
            "**ETF vs. Fixed Income — practical differences:**\n"
            "• Fixed income: predictability, liquidity, lower risk; ideal for reserves and short horizon.\n"
            "• ETFs (broad index funds): wide exposure, low cost, but subject to market volatility.\n"
            "• Conservative profile: mostly fixed income with a small ETF allocation.\n"
            "• Moderate/aggressive profile: progressively more ETFs as time horizon grows.\n"
            "• Tax: ETFs 15% income tax on gain; fixed income uses regressive table (22.5% to 15%)."
        ),
    },
}


def detect_scenario(user_text: str) -> str | None:
    lower = user_text.lower()
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return scenario
    return None


def build_scenario_guidance(user_text: str, language: str) -> str:
    scenario = detect_scenario(user_text)
    if not scenario:
        return ""
    guidance = SCENARIO_GUIDANCE.get(scenario, {})
    return guidance.get(language, guidance.get("en", ""))


# ---------------------------------------------------------------------------
# Transaction extraction from natural language
# ---------------------------------------------------------------------------

_TRANSACTION_VERBS_OUT = [
    "spent",
    "paid",
    "bought",
    "gastei",
    "paguei",
    "comprei",
    "debited",
    "debit",
    "cost",
]
_TRANSACTION_VERBS_IN = [
    "received",
    "earned",
    "got",
    "win",
    "won",
    "recebi",
    "ganhei",
    "ganhou",
]

_AMOUNT_RE = re.compile(
    (
        r"R?\$?\s*"
        r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:[\.,]\d{1,2})?)"
        r"(?!\d)"
        r"\s*"
        r"(mil|k|thousand|thousands|grand|grands|conto|contos)?"
    ),
    re.I,
)

_MAGNITUDE_MULTIPLIERS: dict[str, int] = {
    "mil": 1000,
    "k": 1000,
    "thousand": 1000,
    "thousands": 1000,
    "grand": 1000,
    "grands": 1000,
    "conto": 1000,
    "contos": 1000,
}

_EXPENSE_HINTS = [
    "expense",
    "expenses",
    "despesa",
    "despesas",
    "gasto",
    "gastos",
    "spent",
    "spend",
    "purchase",
    "comprar",
    "compra",
    "food",
    "mercado",
    "ifood",
]

_INCOME_HINTS = [
    "income",
    "salary",
    "freelance",
    "paycheck",
    "receita",
    "salario",
    "renda",
    "recebi",
    "ganhei",
]

_CATEGORY_HINTS: dict[str, list[str]] = {
    "food": [
        "food",
        "breakfast",
        "lunch",
        "dinner",
        "restaurante",
        "ifood",
        "mercado",
        "supermercado",
        "restaurant",
        "grocery",
    ],
    "transport": [
        "uber",
        "bus",
        "subway",
        "metro",
        "gas",
        "fuel",
        "transport",
    ],
    "health": [
        "pharmacy",
        "doctor",
        "consulta",
        "exame",
        "health",
        "appointment",
        "exam",
    ],
    "housing": [
        "rent",
        "condo",
        "electricity",
        "water",
        "internet",
        "utilities",
    ],
    "leisure": [
        "cinema",
        "show",
        "travel",
        "entertainment",
        "netflix",
        "spotify",
    ],
    "education": [
        "education",
        "course",
        "book",
        "school",
        "college",
        "tuition",
    ],
    "salary": ["salary", "payroll", "payslip"],
    "freelance": ["freela", "freelance", "projeto", "cliente", "client"],
    "investments": ["contribution", "investment", "withdrawal", "yield"],
}


def _detect_category(text: str) -> str:
    lower = text.lower()
    for category, hints in _CATEGORY_HINTS.items():
        if any(h in lower for h in hints):
            return category
    return "general"


def _parse_amount(raw: str, magnitude: str = "") -> float | None:
    cleaned = raw.replace(".", "").replace(",", ".")
    try:
        amount = float(cleaned)
        normalized_magnitude = magnitude.lower().strip() if magnitude else ""
        amount *= _MAGNITUDE_MULTIPLIERS.get(normalized_magnitude, 1)
        return amount
    except ValueError:
        return None


def _infer_transaction_type(text: str) -> str:
    lower = text.lower()
    if any(hint in lower for hint in _INCOME_HINTS):
        return "entrada"
    if any(hint in lower for hint in _EXPENSE_HINTS):
        return "saida"
    return "saida"


def is_transaction_message(user_text: str) -> bool:
    lower = user_text.lower()
    has_verb = any(v in lower for v in _TRANSACTION_VERBS_OUT + _TRANSACTION_VERBS_IN)
    has_amount = bool(_AMOUNT_RE.search(user_text))
    return has_verb and has_amount


def extract_transactions_from_message(user_text: str) -> list[dict[str, Any]]:
    """Return a list of transaction dicts {data, valor, categoria, tipo}."""
    verbs = _TRANSACTION_VERBS_OUT + _TRANSACTION_VERBS_IN
    verbs_pattern = "|".join(sorted(map(re.escape, verbs), key=len, reverse=True))
    segment_re = re.compile(
        rf"\b(?P<verb>{verbs_pattern})\b(?P<chunk>.*?)(?=\b(?:{verbs_pattern})\b|$)",
        re.I | re.S,
    )

    transactions: list[dict[str, Any]] = []
    for match in segment_re.finditer(user_text):
        verb = match.group("verb").lower()
        chunk = match.group("chunk") or ""
        amount_match = _AMOUNT_RE.search(chunk)
        if not amount_match:
            continue

        amount = _parse_amount(amount_match.group(1), amount_match.group(2) or "")
        if amount is None or amount <= 0:
            continue

        tipo = "entrada" if verb in _TRANSACTION_VERBS_IN else "saida"
        category = _detect_category(chunk)
        if category == "general":
            category = _detect_category(user_text)

        transactions.append(
            {
                "data": date.today().isoformat(),
                "valor": amount,
                "categoria": category,
                "tipo": tipo,
            }
        )

    if transactions:
        return transactions

    # Fallback for messages where verb/amount segmentation fails.
    amount_match = _AMOUNT_RE.search(user_text)
    if not amount_match:
        return []

    amount = _parse_amount(amount_match.group(1), amount_match.group(2) or "")
    if amount is None or amount <= 0:
        return []

    tipo = _infer_transaction_type(user_text)
    return [
        {
            "data": date.today().isoformat(),
            "valor": amount,
            "categoria": _detect_category(user_text),
            "tipo": tipo,
        }
    ]


def extract_transaction_from_message(user_text: str) -> dict | None:
    """Return a transaction dict {data, valor, categoria, tipo} or None."""
    transactions = extract_transactions_from_message(user_text)
    return transactions[0] if transactions else None


def extract_user_name(user_text: str) -> str | None:
    text = user_text.strip()
    if not text:
        return None

    explicit_match = re.search(
        r"(?:my name is|i am|i'm)\s+([A-Za-zÀ-ÿ' -]{2,40})",
        text,
        re.I,
    )
    if explicit_match:
        return explicit_match.group(1).strip().title()

    cleaned = re.sub(r"[\.,!?;:()\[\]{}\"“”'`´~^*_+=/\\|]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    lower = cleaned.lower()
    disallowed_fragments = [
        "invest",
        "etf",
        "bitcoin",
        "tax",
        "income",
        "goal",
        "help",
        "hello",
        "hi",
    ]
    if any(fragment in lower for fragment in disallowed_fragments):
        return None

    if any(char.isdigit() for char in cleaned):
        return None

    if "?" in text or len(cleaned) > 40:
        return None

    tokens = cleaned.split()
    if not 1 <= len(tokens) <= 3:
        return None

    if not all(re.fullmatch(r"[A-Za-zÀ-ÿ-]{2,20}", token) for token in tokens):
        return None

    return " ".join(token.capitalize() for token in tokens)
