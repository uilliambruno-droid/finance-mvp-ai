from __future__ import annotations

import json
import re
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
        "taxa",
        "taxação",
        "taxacao",
        "imposto",
        "ir",
        "darf",
        "iof",
        "tribut",
        "tax",
        "taxation",
        "capital gain",
    ]
    return any(keyword in lower for keyword in keywords)


def is_portfolio_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "carteira",
        "alocação",
        "alocacao",
        "portfolio",
        "portfólio",
        "diversifica",
        "allocate",
        "allocation",
    ]
    return any(keyword in lower for keyword in keywords)


def is_instrument_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "stock",
        "stocks",
        "ação",
        "acoes",
        "etf",
        "tesouro",
        "selic",
        "cripto",
        "bitcoin",
        "ethereum",
        "renda fixa",
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
        if language == "en":
            return (
                "Portfolio guidance for this moment: prioritize financial stability first. "
                "Focus on essential spending, emergency cash, and income generation before taking market risk."
            )
        return (
            "Guia de carteira para este momento: priorize estabilidade financeira primeiro. "
            "Foque em gastos essenciais, caixa de emergência e geração de renda antes de tomar risco de mercado."
        )

    if investor_profile.startswith("conserv"):
        target_mix = "70% renda fixa / 20% ETFs amplos / 10% proteção e caixa"
        categories = {"renda_fixa", "etf", "fundo"}
    elif investor_profile.startswith("moder"):
        target_mix = "50% renda fixa / 35% ETFs e ações globais / 15% satélites"
        categories = {"renda_fixa", "etf", "acao", "fundo"}
    else:
        target_mix = "30% renda fixa / 50% ETFs e ações / 20% satélites (incluindo cripto com limite)"
        categories = {"renda_fixa", "etf", "acao", "cripto", "fundo"}

    selected_products = _find_products_by_category(products, categories)[:6]
    names = [
        str(item.get("nome", "")) for item in selected_products if item.get("nome")
    ]

    if language == "en":
        lines = [f"Suggested educational allocation mix: {target_mix}."]
        if names:
            lines.append("Examples from current catalog: " + ", ".join(names) + ".")
        lines.append(
            "Use position sizing and diversification; avoid concentrating in one single asset."
        )
        return " ".join(lines)

    lines = [f"Mix de alocação educativa sugerido: {target_mix}."]
    if names:
        lines.append("Exemplos no catálogo atual: " + ", ".join(names) + ".")
    lines.append(
        "Use diversificação e controle de posição; evite concentrar em um único ativo."
    )
    return " ".join(lines)


def build_tax_guidance(tax_knowledge: dict[str, Any], language: str) -> str:
    if not tax_knowledge:
        return ""

    tax_br = tax_knowledge.get("taxacao_brasil", {})
    ir_table = tax_br.get("renda_fixa_regressiva_ir", [])

    if language == "en":
        parts = [
            "Taxation essentials:",
            "Brazilian fixed income often uses a regressive income tax schedule by holding period.",
            "Current scope is Brazil-first, so taxation guidance is focused on Brazilian rules.",
        ]
        if ir_table:
            parts.append("Reference brackets: " + " | ".join(ir_table) + ".")
        parts.append(str(tax_br.get("iof", "")))
        return " ".join(part for part in parts if part)

    parts = [
        "Noções de taxação:",
        "Na renda fixa brasileira, normalmente há IR regressivo por prazo.",
        "Escopo atual Brasil-first: a orientação tributária prioriza regras brasileiras.",
    ]
    if ir_table:
        parts.append("Faixas de referência: " + " | ".join(ir_table) + ".")
    iof_text = str(tax_br.get("iof", ""))
    if iof_text:
        parts.append("IOF: " + iof_text)
    return " ".join(part for part in parts if part)


def build_instrument_guidance(tax_knowledge: dict[str, Any], language: str) -> str:
    if not tax_knowledge:
        return ""

    selic = tax_knowledge.get("selic", {})
    tesouro = tax_knowledge.get("tesouro_direto", {})

    if language == "en":
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

    parts = [
        "Notas sobre produtos:",
        str(selic.get("descricao", "")),
        str(selic.get("uso_pratico", "")),
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
        "reserva de emergência",
        "reserva emergencia",
        "emergency fund",
        "reserva financeira",
        "colchão financeiro",
    ],
    "dividas_vs_investir": [
        "dívida",
        "divida",
        "quitar",
        "empréstimo",
        "emprestimo",
        "financiamento",
        "debt",
        "loan",
        "pay off",
    ],
    "aportes_mensais": [
        "aporte",
        "aportes",
        "investir todo mês",
        "investir mensalmente",
        "quanto investir",
        "monthly investment",
        "contribute monthly",
    ],
    "aposentadoria": [
        "aposentadoria",
        "previdência",
        "previdencia",
        "independência financeira",
        "independencia financeira",
        "retire",
        "retirement",
        "longo prazo",
    ],
    "etf_vs_renda_fixa": [
        "etf vs",
        "renda fixa vs",
        "vs etf",
        "vs renda fixa",
        "comparar",
        "comparação",
        "compare etf",
        "etf ou renda fixa",
    ],
}

SCENARIO_GUIDANCE: dict[str, dict[str, str]] = {
    "reserva_emergencia": {
        "pt": (
            "**Reserva de Emergência — como montar:**\n"
            "• Meta: 6× seus gastos mensais em ativos de alta liquidez (Tesouro Selic, CDB liquidez diária).\n"
            "• Para quem tem renda variável ou autônomo: prefira 9–12×.\n"
            "• Não comprometa a reserva com investimentos de risco — ela é proteção, não rendimento.\n"
            "• Só depois de montar a reserva, direcione o excedente para carteira de crescimento."
        ),
        "en": (
            "**Emergency Fund — how to build it:**\n"
            "• Target: 6× monthly expenses in highly liquid assets (Tesouro Selic, daily-liquidity CDB).\n"
            "• For freelancers or variable income: aim for 9–12×.\n"
            "• Never use the emergency fund for risky investments — it's protection, not yield.\n"
            "• Only after the fund is built, allocate surplus to growth portfolios."
        ),
    },
    "dividas_vs_investir": {
        "pt": (
            "**Dívidas vs. Investir — como decidir:**\n"
            "• Se a taxa da dívida > taxa de retorno esperada do investimento → quite primeiro.\n"
            "• Cartão de crédito/rotativo (juros > 12% a.m.): quite urgente, sem negociação.\n"
            "• Financiamento imobiliário (juros < Selic): pode investir em paralelo.\n"
            "• Regra prática: quite dívidas acima de CDI antes de investir em renda variável."
        ),
        "en": (
            "**Debt vs. Invest — how to decide:**\n"
            "• If debt rate > expected investment return → pay off debt first.\n"
            "• Credit card/revolving debt (>12% p.m.): urgent payoff, no negotiation.\n"
            "• Mortgage (rate < Selic): investing in parallel may work.\n"
            "• Rule of thumb: pay off debts above CDI rate before investing in variable income."
        ),
    },
    "aportes_mensais": {
        "pt": (
            "**Aportes Mensais — estratégia:**\n"
            "• Use o método Dollar Cost Averaging (DCA): aporte fixo todo mês, independente do mercado.\n"
            "• Sugestão de divisão: 50% renda fixa (Tesouro, CDB) + 30% ETFs (BOVA11, IVVB11) + 20% flexível.\n"
            "• Automatize o aporte logo após receber a renda — pague-se primeiro.\n"
            "• Revise a alocação a cada 6–12 meses conforme seu perfil mudar."
        ),
        "en": (
            "**Monthly Contributions — strategy:**\n"
            "• Use Dollar Cost Averaging (DCA): fixed contribution each month regardless of market.\n"
            "• Suggested split: 50% fixed income (Tesouro, CDB) + 30% ETFs + 20% flexible.\n"
            "• Automate contributions right after payday — pay yourself first.\n"
            "• Review allocation every 6–12 months as your profile evolves."
        ),
    },
    "aposentadoria": {
        "pt": (
            "**Aposentadoria / Independência Financeira:**\n"
            "• Regra dos 25×: acumule 25× suas despesas anuais para independência financeira.\n"
            "• Previdência privada (PGBL vs VGBL): PGBL para quem usa declaração completa de IR; VGBL para os demais.\n"
            "• Prazo longo favorece renda variável no início e migração gradual para renda fixa ao aproximar da meta.\n"
            "• Considere Tesouro IPCA+ como âncora de longo prazo para proteger o poder de compra."
        ),
        "en": (
            "**Retirement / Financial Independence:**\n"
            "• 25× rule: accumulate 25× your annual expenses for financial independence.\n"
            "• Private pension (PGBL vs VGBL): PGBL for those using full tax deduction; VGBL for others.\n"
            "• Long horizon favors equities early, gradually shifting to fixed income as you near the goal.\n"
            "• Consider Tesouro IPCA+ as a long-term anchor to protect purchasing power."
        ),
    },
    "etf_vs_renda_fixa": {
        "pt": (
            "**ETF vs. Renda Fixa — diferenças práticas:**\n"
            "• Renda fixa: previsibilidade, liquidez, menor risco; ideal para reserva e horizonte curto.\n"
            "• ETFs (BOVA11, IVVB11, etc.): exposição ampla, custo baixo, mas com volatilidade de mercado.\n"
            "• Para perfil conservador: predominância de renda fixa com pequena fatia em ETFs.\n"
            "• Para perfil moderado/arrojado: aumento progressivo em ETFs conforme horizonte cresce.\n"
            "• Imposto: ETFs têm IR 15% sobre ganho; renda fixa tem tabela regressiva (22,5% a 15%)."
        ),
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
    return guidance.get(language, guidance.get("pt", ""))


# ---------------------------------------------------------------------------
# Transaction extraction from natural language
# ---------------------------------------------------------------------------

_TRANSACTION_VERBS_OUT = [
    "gastei",
    "paguei",
    "comprei",
    "gasto",
    "saiu",
    "spent",
    "paid",
    "bought",
]
_TRANSACTION_VERBS_IN = [
    "recebi",
    "ganhei",
    "entrou",
    "recebo",
    "faturei",
    "received",
    "earned",
    "got",
]

_AMOUNT_RE = re.compile(
    r"R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.I,
)

_CATEGORY_HINTS: dict[str, list[str]] = {
    "alimentação": [
        "comida",
        "almoço",
        "jantar",
        "cafe",
        "restaurante",
        "ifood",
        "mercado",
        "supermercado",
        "food",
        "lunch",
        "dinner",
    ],
    "transporte": [
        "uber",
        "ônibus",
        "onibus",
        "metrô",
        "metro",
        "gasolina",
        "combustivel",
        "combustível",
        "transport",
    ],
    "saúde": [
        "farmácia",
        "farmacia",
        "médico",
        "medico",
        "consulta",
        "exame",
        "health",
        "pharmacy",
        "doctor",
    ],
    "moradia": [
        "aluguel",
        "condomínio",
        "condominio",
        "luz",
        "água",
        "agua",
        "internet",
        "rent",
        "utilities",
    ],
    "lazer": [
        "cinema",
        "show",
        "viagem",
        "viagem",
        "entretenimento",
        "netflix",
        "spotify",
        "entertainment",
        "travel",
    ],
    "educação": [
        "curso",
        "livro",
        "escola",
        "faculdade",
        "mensalidade",
        "education",
        "course",
    ],
    "salário": ["salário", "salario", "salary", "holerite"],
    "freelance": ["freela", "freelance", "projeto", "cliente", "client"],
    "investimento": ["aporte", "investimento", "resgate", "rendimento"],
}


def _detect_category(text: str) -> str:
    lower = text.lower()
    for category, hints in _CATEGORY_HINTS.items():
        if any(h in lower for h in hints):
            return category
    return "geral"


def _parse_amount(raw: str) -> float | None:
    cleaned = raw.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def is_transaction_message(user_text: str) -> bool:
    lower = user_text.lower()
    has_verb = any(v in lower for v in _TRANSACTION_VERBS_OUT + _TRANSACTION_VERBS_IN)
    has_amount = bool(_AMOUNT_RE.search(user_text))
    return has_verb and has_amount


def extract_transaction_from_message(user_text: str) -> dict | None:
    """Return a transaction dict {data, valor, categoria, tipo} or None."""
    lower = user_text.lower()

    amount_match = _AMOUNT_RE.search(user_text)
    if not amount_match:
        return None
    amount = _parse_amount(amount_match.group(1))
    if not amount:
        return None

    tipo = "entrada" if any(v in lower for v in _TRANSACTION_VERBS_IN) else "saida"
    category = _detect_category(user_text)
    today = __import__("datetime").date.today().isoformat()

    return {
        "data": today,
        "valor": amount,
        "categoria": category,
        "tipo": tipo,
    }


def extract_user_name(user_text: str) -> str | None:
    text = user_text.strip()
    if not text:
        return None

    explicit_match = re.search(
        r"(?:meu nome é|me chamo|my name is|i am|i'm|sou)\s+([A-Za-zÀ-ÿ' -]{2,40})",
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
        "quero",
        "preciso",
        "invest",
        "etf",
        "ação",
        "acoes",
        "bitcoin",
        "carteira",
        "tax",
        "imposto",
        "renda",
        "income",
        "goal",
        "objetivo",
        "help",
        "ajuda",
        "oi",
        "olá",
        "ola",
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
