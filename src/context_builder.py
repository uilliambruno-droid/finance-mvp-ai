"""Context and prompt assembly for LLM calls."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from config import (
    LLM_CONTEXT_PRODUCTS,
    LLM_CONTEXT_RECENT_MESSAGES,
    LLM_CONTEXT_TOP_CATEGORIES,
)
from state import empty_transactions


def build_context(
    profile: dict[str, Any],
    transactions: pd.DataFrame,
    products: list[dict[str, Any]],
    history: pd.DataFrame,
) -> str:
    if transactions.empty:
        expense_df = empty_transactions()
    else:
        expense_df = transactions[transactions["tipo"] == "saida"].copy()

    total_expenses = float(expense_df["valor"].sum()) if not expense_df.empty else 0.0
    by_category = (
        expense_df.groupby("categoria", as_index=False)["valor"]
        .sum()
        .sort_values("valor", ascending=False)
        if not expense_df.empty
        else pd.DataFrame(columns=["categoria", "valor"])
    )
    top_categories = by_category.head(LLM_CONTEXT_TOP_CATEGORIES).to_dict(
        orient="records"
    )

    products_view = []
    for item in products[:LLM_CONTEXT_PRODUCTS]:
        products_view.append(
            {
                "nome": item.get("nome"),
                "categoria": item.get("categoria"),
                "risco": item.get("risco"),
                "mercado": item.get("mercado"),
                "moeda": item.get("moeda"),
                "alerta_risco": item.get("alerta_risco"),
            }
        )

    context = {
        "cliente": {
            "nome": profile.get("nome"),
            "renda_mensal": profile.get("renda_mensal"),
            "fonte_renda": profile.get("fonte_renda"),
            "sem_renda": profile.get("sem_renda"),
            "desempregado": profile.get("desempregado"),
            "perfil_investidor": profile.get("perfil_investidor"),
            "aceita_risco": profile.get("aceita_risco"),
            "patrimonio_atual": profile.get("patrimonio_atual"),
            "meta_patrimonial": profile.get("meta_patrimonial"),
            "prazo_meta_meses": profile.get("prazo_meta_meses"),
            "valor_faltante_meta": (
                max(
                    float(profile.get("meta_patrimonial") or 0.0)
                    - float(profile.get("patrimonio_atual") or 0.0),
                    0.0,
                )
                if profile.get("meta_patrimonial") not in (None, "")
                else None
            ),
            "aporte_mensal_necessario": (
                round(
                    max(
                        float(profile.get("meta_patrimonial") or 0.0)
                        - float(profile.get("patrimonio_atual") or 0.0),
                        0.0,
                    )
                    / float(profile.get("prazo_meta_meses") or 1),
                    2,
                )
                if profile.get("meta_patrimonial") not in (None, "")
                and profile.get("prazo_meta_meses") not in (None, "", 0)
                else None
            ),
            "observacoes": profile.get("observacoes", ""),
        },
        "gastos": {
            "total_saidas": total_expenses,
            "top_categorias": top_categories,
            "quantidade_transacoes": int(len(transactions)),
        },
        "produtos_catalogo": products_view,
        "historico_atendimento_linhas": int(len(history)) if not history.empty else 0,
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def build_recent_messages(
    messages: list[dict[str, str]], limit: int = LLM_CONTEXT_RECENT_MESSAGES
) -> list[dict[str, str]]:
    recent = messages[-limit:]
    cleaned: list[dict[str, str]] = []
    for message in recent:
        role = message.get("role", "user")
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


def build_llm_messages(
    system_prompt: str,
    context: str,
    user_text: str,
    conversation_messages: list[dict[str, str]],
    language: str,
    market_snapshot: str = "",
    finance_knowledge_context: str = "",
) -> list[dict[str, str]]:
    instructions = (
        "ALWAYS reply in English, even if the user writes in Portuguese or mixed language. "
        "Never answer in Portuguese. If needed, translate your own draft to English before sending. "
        "Keep the conversation natural, warm, playful, and continuous. "
        "Act like an experienced financial consultant, not a generic chatbot. "
        "Answer directly, with practical judgment on portfolios, fees, taxes, and financial planning. "
        "Do not use menu-like options or a robotic tone. "
        "Use light humor and an upbeat style when appropriate, without sounding childish. "
        "If the user says they are unemployed or have no income, do not push for income details right away; "
        "guide them toward essential expenses, stability, and realistic next steps. "
        "This assistant is Brazil-first: prioritize Brazilian products, regulation, and tax context. "
        "If the user asks for non-Brazil jurisdictions, explain scope limitations and bring it back to Brazil context. "
        "Use the provided context only for grounding and never invent facts."
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": instructions},
        {
            "role": "system",
            "content": (
                "STRUCTURED USER CONTEXT:\n"
                f"{context}\n\n"
                "Use this context to personalize the answer safely."
            ),
        },
    ]
    if market_snapshot:
        messages.append(
            {
                "role": "system",
                "content": (
                    "RECENT MARKET PRICE DATA TO USE IN THE ANSWER (if relevant):\n"
                    f"{market_snapshot}"
                ),
            }
        )
    if finance_knowledge_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "CURATED FINANCIAL KNOWLEDGE BASE (use when relevant):\n"
                    f"{finance_knowledge_context}"
                ),
            }
        )
    messages.extend(conversation_messages)
    messages.append({"role": "user", "content": user_text})
    return messages
