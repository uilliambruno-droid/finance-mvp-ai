from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from finance_knowledge import (  # noqa: E402
    build_finance_knowledge_context,
    build_portfolio_guidance,
    build_tax_guidance,
    extract_transactions_from_message,
    extract_user_name,
    is_transaction_message,
    is_instrument_query,
    is_portfolio_query,
    is_tax_query,
    load_tax_knowledge,
)


def load_products() -> list[dict]:
    file_path = ROOT / "data" / "produtos_financeiros.json"
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def test_query_detectors() -> None:
    assert is_tax_query("How does ETF taxation and IOF work?")
    assert is_portfolio_query("Build a portfolio for me")
    assert is_instrument_query("Explain Treasury Selic and ETFs")


def test_load_tax_knowledge() -> None:
    knowledge = load_tax_knowledge(ROOT)
    assert "taxacao_brasil" in knowledge
    assert "selic" in knowledge


def test_portfolio_guidance_conservative() -> None:
    profile = {
        "perfil_investidor": "Conservative",
        "sem_renda": False,
        "desempregado": False,
    }
    guidance = build_portfolio_guidance(profile, load_products(), language="en")
    assert "Suggested educational allocation mix" in guidance
    assert "fixed income" in guidance.lower()


def test_portfolio_guidance_no_income() -> None:
    profile = {
        "perfil_investidor": "Moderate",
        "sem_renda": True,
        "desempregado": True,
    }
    guidance = build_portfolio_guidance(profile, load_products(), language="en")
    assert "stability" in guidance.lower()
    assert "income generation" in guidance.lower()


def test_tax_guidance_contains_reference() -> None:
    knowledge = load_tax_knowledge(ROOT)
    guidance = build_tax_guidance(knowledge, language="en")
    assert "regressive income tax" in guidance
    assert "IOF" in guidance


def test_knowledge_context_for_tax_and_portfolio() -> None:
    profile = {
        "perfil_investidor": "Moderate",
        "sem_renda": False,
        "desempregado": False,
        "objetivo_principal": "growth",
    }
    context = build_finance_knowledge_context(
        user_text="I want to build a portfolio with ETF and understand taxation",
        profile=profile,
        products=load_products(),
        tax_knowledge=load_tax_knowledge(ROOT),
        language="en",
    )
    assert "Taxation essentials" in context
    assert "Suggested educational allocation mix" in context


def test_extract_user_name_direct_answer() -> None:
    assert extract_user_name("uilliam") == "Uilliam"
    assert extract_user_name("my name is ana maria") == "Ana Maria"


def test_extract_user_name_ignores_finance_phrase() -> None:
    assert extract_user_name("i want to invest in ETF") is None


def test_extract_transaction_thousands_in_english_plural() -> None:
    message = "today I spent 2 thousands on shit foods"
    transactions = extract_transactions_from_message(message)

    assert len(transactions) == 1
    assert transactions[0]["tipo"] == "saida"
    assert transactions[0]["categoria"] == "food"
    assert transactions[0]["valor"] == 2000.0


def test_extract_transaction_contos_in_portuguese() -> None:
    message = "gastei 3 contos no mercado"
    transactions = extract_transactions_from_message(message)

    assert len(transactions) == 1
    assert transactions[0]["tipo"] == "saida"
    assert transactions[0]["categoria"] == "food"
    assert transactions[0]["valor"] == 3000.0


def test_is_transaction_message_accepts_portuguese_expense_verb() -> None:
    assert is_transaction_message("paguei 250 no uber")
