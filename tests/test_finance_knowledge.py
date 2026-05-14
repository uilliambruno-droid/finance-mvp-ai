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
    extract_user_name,
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
    assert is_tax_query("Como funciona a taxação de ETF e IOF?")
    assert is_portfolio_query("Monta uma carteira para mim")
    assert is_instrument_query("Explique Tesouro Selic e ETFs")


def test_load_tax_knowledge() -> None:
    knowledge = load_tax_knowledge(ROOT)
    assert "taxacao_brasil" in knowledge
    assert "selic" in knowledge


def test_portfolio_guidance_conservative() -> None:
    profile = {
        "perfil_investidor": "Conservador",
        "sem_renda": False,
        "desempregado": False,
    }
    guidance = build_portfolio_guidance(profile, load_products(), language="pt")
    assert "Mix de alocação" in guidance
    assert "renda fixa" in guidance.lower()


def test_portfolio_guidance_no_income() -> None:
    profile = {
        "perfil_investidor": "Moderado",
        "sem_renda": True,
        "desempregado": True,
    }
    guidance = build_portfolio_guidance(profile, load_products(), language="pt")
    assert "estabilidade" in guidance.lower()
    assert "geração de renda" in guidance.lower()


def test_tax_guidance_contains_reference() -> None:
    knowledge = load_tax_knowledge(ROOT)
    guidance = build_tax_guidance(knowledge, language="pt")
    assert "IR regressivo" in guidance
    assert "IOF" in guidance


def test_knowledge_context_for_tax_and_portfolio() -> None:
    profile = {
        "perfil_investidor": "Moderado",
        "sem_renda": False,
        "desempregado": False,
        "objetivo_principal": "crescimento",
    }
    context = build_finance_knowledge_context(
        user_text="Quero montar carteira com ETF e entender taxação",
        profile=profile,
        products=load_products(),
        tax_knowledge=load_tax_knowledge(ROOT),
        language="pt",
    )
    assert "Noções de taxação" in context
    assert "Mix de alocação" in context


def test_extract_user_name_direct_answer() -> None:
    assert extract_user_name("uilliam") == "Uilliam"
    assert extract_user_name("me chamo ana maria") == "Ana Maria"


def test_extract_user_name_ignores_finance_phrase() -> None:
    assert extract_user_name("quero investir em ETF") is None


def test_extract_user_name_ignores_greeting_oi() -> None:
    assert extract_user_name("oi") is None
