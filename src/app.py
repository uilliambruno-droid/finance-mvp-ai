from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from finance_knowledge import (
    build_finance_knowledge_context,
    extract_user_name,
    extract_transaction_from_message,
    is_transaction_message,
    load_tax_knowledge,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
RUNTIME_DIR = DATA_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "user_state.json"
EVENTS_LOG_FILE = RUNTIME_DIR / "events.jsonl"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct")

HIDE_STREAMLIT_CHROME = """
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppToolbar {display: none;}
    [data-testid="stToolbar"] {display: none;}
    .stDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stChatMessageAvatar"] {display: none;}
    [data-testid="stChatMessageContent"] {margin-left: 0 !important;}
</style>
"""


logger = logging.getLogger("pluto_app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


TEXTS = {
    "pt": {
        "caption": "Assistente financeiro conversacional, educativo e pensado para acompanhar cada pessoa no próprio ritmo.",
        "intake_title": "Antes do chat, vamos montar seu perfil financeiro rapidinho.",
        "intake_caption": "Preencha o formulário uma vez e o Pluto libera o chat já com o seu contexto. Sem ficar pedindo nome toda hora.",
        "intake_submit": "Liberar chat com meu perfil",
        "intake_name": "Nome",
        "intake_has_income": "Tenho renda mensal",
        "intake_income": "Renda mensal aproximada (R$)",
        "intake_profile": "Estilo de investidor",
        "intake_profile_conservative": "Conservador",
        "intake_profile_moderate": "Moderado",
        "intake_profile_aggressive": "Arrojado",
        "intake_spending": "Gastos mensais aproximados (R$)",
        "intake_has_spending": "Tenho gastos fixos / consumo recorrente",
        "intake_goal": "Objetivo principal",
        "intake_current_wealth": "Patrimônio atual (R$)",
        "intake_target_wealth": "Meta patrimonial (R$)",
        "intake_goal_progress": "Progresso da meta",
        "wealth_current_label": "Patrimônio",
        "wealth_target_label": "Meta",
        "wealth_missing_label": "Falta",
        "intake_income_source": "Fonte de renda",
        "intake_notes": "Observações opcionais",
        "intake_ready_title": "Perfil carregado",
        "intake_ready_caption": "Agora o chat está liberado com seu contexto. O Pluto já sabe o básico e pode ir direto para a consultoria.",
        "intake_missing_warning": "Preencha pelo menos nome, renda ou situação de renda, estilo e objetivo para liberar o chat.",
        "consultant_welcome": "Perfeito. Agora eu tenho seu perfil e posso falar como consultor financeiro, sem enrolação.",
        "chat_locked": "Antes de liberar o chat, preciso de um perfil mínimo para personalizar as respostas.",
        "welcome": "Oi! Eu sou o Pluto 🪐 Qual é o seu nome?",
        "welcome_quick": "Oi! Eu sou o Pluto 🪐 Me conta direto o que você quer resolver hoje nas suas finanças no Brasil.",
        "brazil_focus_notice": "🇧🇷 Estamos migrando para foco total em Brasil: produtos, regras e educação financeira priorizam o contexto brasileiro. Posso responder em inglês, mas o conteúdo continua Brasil-first.",
        "english_toggle_label": "Responder em inglês / Reply in English",
        "chat_mode_label": "Modo da conversa",
        "chat_mode_guided": "Guiado (Pluto pergunta e estrutura junto)",
        "chat_mode_quick": "Rápido (direto ao ponto)",
        "state_restored": "Sessão anterior restaurada com sucesso.",
        "state_restore_error": "Não consegui restaurar sua sessão anterior; vamos começar daqui.",
        "state_save_error": "Não consegui salvar o estado da sessão agora.",
        "chat_placeholder": "Converse com o Pluto sobre planejamento, gastos, renda ou investimentos...",
        "csv_title": "Quer me mandar seus gastos?",
        "csv_caption": "Se preferir, você pode enviar um CSV com suas transações e eu analiso seus gastos sem te fazer preencher formulário.",
        "upload_label": "Enviar CSV de transações",
        "upload_help": "Colunas aceitas: data/date, valor/amount, categoria/category, tipo/type.",
        "upload_success": "CSV carregado com sucesso. Já posso usar esses dados nas próximas respostas.",
        "upload_error": "Não consegui ler esse CSV. Verifique o arquivo e tente novamente.",
        "profile_summary": "Contexto que já entendi sobre você",
        "profile_empty": "Ainda estou te conhecendo.",
        "metrics_profile": "Contexto mapeado",
        "metrics_interactions": "Interações",
        "metrics_transactions": "Transações",
        "feedback_title": "Essa resposta ajudou?",
        "feedback_positive": "Ajudou",
        "feedback_negative": "Ainda não",
        "feedback_saved": "Obrigado pelo feedback — vou usar isso para melhorar o Pluto.",
        "feedback_rating_label": "Nota (1–5)",
        "feedback_comment_label": "Quer escrever algo? (opcional)",
        "feedback_comment_placeholder": "Ex: faltou detalhe sobre X, ou: resposta perfeita!",
        "feedback_submit": "Enviar feedback",
        "price_unavailable": "Não consegui puxar cotação em tempo real agora. Se quiser, tento novamente em instantes.",
        "price_snapshot_title": "📈 Snapshot rápido de mercado",
        "risk_warning": "📌 Aviso: conteúdo educacional, não recomendação profissional de investimento. Ativos de mercado podem oscilar e gerar perdas.",
        "unknown_assets": "⚠️ Nota de segurança: encontrei ativos fora do catálogo atual ({assets}). Posso explicar de forma educativa, mas sem recomendar algo não catalogado.",
        "investor_context": "Contexto do seu perfil: {profile}. Se quiser, posso adaptar a resposta para um nível mais conservador ou mais arrojado.",
        "fallback_greeting": "Oi! Tudo bem por aqui também 🪐 Estou sem acesso ao modelo agora, mas continuo pronto para te ajudar com planejamento, gastos e próximos passos.",
        "fallback_general": "Estou sem conexão com o modelo neste momento, mas posso continuar com você. Me diga o que quer analisar e eu sigo com o que já tenho.",
        "short_answer": " Me conta um pouco mais do que você quer resolver para eu te responder com mais precisão.",
        "rate_limit_notice": "⚠️ O limite de consultas neste momento foi atingido. Tente novamente daqui a pouco ou entre em contato com o desenvolvedor para um plano com mais requisições.",
        "transaction_recorded": "Registrei: **{tipo}** de **R$ {valor:.2f}** em **{categoria}** ({data}).",
        "transaction_recorded_caption": "Anotado no seu histórico. Pode continuar conversando normalmente.",
        "edit_profile": "Editar perfil",
        "unemployment_support": "Se você está desempregado ou sem renda agora, o foco primeiro não precisa ser investir. Posso te ajudar a organizar gastos essenciais, pensar em fontes de renda e montar um plano simples sem desanimar.",
        "no_income_prompt": "Nesse momento, vale priorizar caixa, gastos essenciais e caminhos para gerar renda antes de pensar em risco financeiro.",
        "updated_profile": "Anotei isso sobre você: {fields}.",
    },
    "en": {
        "caption": "A conversational financial assistant designed to support each person at their own pace.",
        "intake_title": "Before chat, let’s build your financial profile quickly.",
        "intake_caption": "Fill out the form once and Pluto unlocks chat with your context. No need to keep asking for your name.",
        "intake_submit": "Unlock chat with my profile",
        "intake_name": "Name",
        "intake_has_income": "I have monthly income",
        "intake_income": "Approximate monthly income (R$)",
        "intake_profile": "Investor style",
        "intake_profile_conservative": "Conservative",
        "intake_profile_moderate": "Moderate",
        "intake_profile_aggressive": "Aggressive",
        "intake_spending": "Approximate monthly expenses (R$)",
        "intake_has_spending": "I have fixed expenses / recurring spending",
        "intake_goal": "Main goal",
        "intake_current_wealth": "Current net worth (R$)",
        "intake_target_wealth": "Target net worth (R$)",
        "intake_goal_progress": "Goal progress",
        "wealth_current_label": "Net worth",
        "wealth_target_label": "Target",
        "wealth_missing_label": "Missing",
        "intake_income_source": "Income source",
        "intake_notes": "Optional notes",
        "intake_ready_title": "Profile loaded",
        "intake_ready_caption": "Chat is now unlocked with your context. Pluto already knows the basics and can jump straight into consulting.",
        "intake_missing_warning": "Fill at least name, income or income status, style and goal to unlock chat.",
        "consultant_welcome": "Perfect. I have your profile now and can speak like a financial consultant, no fluff.",
        "chat_locked": "Before I unlock chat, I need a minimal profile so I can personalize the answers.",
        "welcome": "Hi! I’m Pluto 🪐 What is your name?",
        "welcome_quick": "Hi! I’m Pluto 🪐 Tell me directly what you want to solve today in your Brazil-focused finances.",
        "brazil_focus_notice": "🇧🇷 We are moving to a Brazil-only focus: products, rules, and financial education prioritize the Brazilian context. I can reply in English, but the content remains Brazil-first.",
        "english_toggle_label": "Reply in English / Responder em inglês",
        "chat_mode_label": "Conversation mode",
        "chat_mode_guided": "Guided (Pluto asks and structures with you)",
        "chat_mode_quick": "Quick (straight to the point)",
        "state_restored": "Previous session restored successfully.",
        "state_restore_error": "I couldn't restore your previous session; we can continue from here.",
        "state_save_error": "I couldn't save session state right now.",
        "chat_placeholder": "Talk to Pluto about planning, spending, income, or investing...",
        "csv_title": "Want to send your spending data?",
        "csv_caption": "If you prefer, you can upload a CSV with your transactions and I’ll analyze your spending without making you fill out a form.",
        "upload_label": "Upload transactions CSV",
        "upload_help": "Accepted columns: data/date, valor/amount, categoria/category, tipo/type.",
        "upload_success": "CSV uploaded successfully. I can use this data in the next answers.",
        "upload_error": "I couldn't read that CSV. Please check the file and try again.",
        "profile_summary": "What I already understand about you",
        "profile_empty": "I’m still getting to know you.",
        "metrics_profile": "Context mapped",
        "metrics_interactions": "Interactions",
        "metrics_transactions": "Transactions",
        "feedback_title": "Did this answer help?",
        "feedback_positive": "Helpful",
        "feedback_negative": "Not yet",
        "feedback_saved": "Thanks for the feedback — I’ll use it to improve Pluto.",
        "feedback_rating_label": "Rating (1–5)",
        "feedback_comment_label": "Want to add a note? (optional)",
        "feedback_comment_placeholder": "E.g.: missing detail on X, or: perfect answer!",
        "feedback_submit": "Send feedback",
        "price_unavailable": "I couldn't fetch live prices right now. If you want, I can try again in a moment.",
        "price_snapshot_title": "📈 Quick market snapshot",
        "risk_warning": "📌 Note: educational content only, not professional investment advice. Market assets can fluctuate and lead to losses.",
        "unknown_assets": "⚠️ Safety note: I found assets outside the current catalog ({assets}). I can explain them educationally, but I won't recommend uncatalogued assets.",
        "investor_context": "Investor profile context: {profile}. If you want, I can adapt the answer to a more conservative or more aggressive style.",
        "fallback_greeting": "Hi! I’m doing well too 🪐 I can't reach the model right now, but I can still help with planning, spending, and next steps.",
        "fallback_general": "I can't reach the model right now, but I can still help. Tell me what you want to analyze and I’ll work with the information I have.",
        "short_answer": " Tell me a bit more about what you want to solve so I can answer more precisely.",
        "rate_limit_notice": "⚠️ The consultation limit for this moment has been reached. Please wait a bit and try again, or contact the developer for a plan with more requests.",
        "followup_goal": "If it helps, tell me what your main financial goal is right now. That helps me guide you better.",
        "followup_income_source": "If you want, you can also tell me how your income comes in today: salary, freelance work, your own business, or no income right now.",
        "followup_income_amount": "If you're comfortable sharing it, your monthly income helps me suggest more realistic priorities and goals.",
        "followup_profile": "If you want, I can also adapt my answers to your risk style — more conservative, moderate, or aggressive.",
        "followup_csv": "And if it’s easier, you can upload a CSV with your spending right below so I can analyze everything from the data.",
        "followup_name": "Before we continue, what is your name?",
        "unemployment_support": "If you're unemployed or without income right now, the first priority does not need to be investing. I can help you organize essential spending, think about income options, and build a simple plan without losing momentum.",
        "no_income_prompt": "For now, it makes sense to prioritize cash, essential expenses, and ways to generate income before thinking about financial risk.",
        "updated_profile": "I noted this about you: {fields}.",
        "transaction_recorded": "Recorded: **{tipo}** of **R$ {valor:.2f}** in **{categoria}** ({data}).",
        "transaction_recorded_caption": "Logged to your history. You can keep chatting normally.",
        "edit_profile": "Edit profile",
    },
}


@st.cache_data
def load_products() -> list[dict[str, Any]]:
    file_path = DATA_DIR / "produtos_financeiros.json"
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_history() -> pd.DataFrame:
    file_path = DATA_DIR / "historico_atendimento.csv"
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


@st.cache_data
def load_tax_knowledge_data() -> dict[str, Any]:
    return load_tax_knowledge(BASE_DIR)


@st.cache_data
def extract_system_prompt() -> str:
    prompt_file = DOCS_DIR / "03-prompts.md"
    if not prompt_file.exists():
        return (
            "Você é o Pluto, assistente financeiro seguro e educativo. "
            "Use apenas dados fornecidos, não invente ativos e sempre inclua alerta de risco."
        )

    text = prompt_file.read_text(encoding="utf-8")
    marker = "## System Prompt"
    if marker not in text:
        return (
            "Você é o Pluto, assistente financeiro seguro e educativo. "
            "Use apenas dados fornecidos e seja prudente."
        )

    after = text.split(marker, 1)[1]
    match = re.search(r"```\s*(.*?)```", after, re.S)
    if not match:
        return (
            "Você é o Pluto, assistente financeiro seguro e educativo. "
            "Use apenas dados fornecidos e seja prudente."
        )

    return match.group(1).strip()


def get_texts(language: str) -> dict[str, Any]:
    return TEXTS.get(language, TEXTS["pt"])


def default_user_profile() -> dict[str, Any]:
    return {
        "nome": "",
        "renda_mensal": None,
        "fonte_renda": "",
        "sem_renda": False,
        "desempregado": False,
        "perfil_investidor": "",
        "aceita_risco": None,
        "objetivo_principal": "",
        "patrimonio_atual": None,
        "meta_patrimonial": None,
        "gastos_mensais": None,
        "tem_gastos": None,
        "perfil_pronto": False,
        "observacoes": "",
    }


def empty_transactions() -> pd.DataFrame:
    return pd.DataFrame(columns=["data", "valor", "categoria", "tipo"])


def profile_is_ready(profile: dict[str, Any]) -> bool:
    has_income = profile.get("renda_mensal") not in (None, "") or profile.get(
        "sem_renda"
    )
    return bool(
        profile.get("nome")
        and has_income
        and profile.get("perfil_investidor")
        and profile.get("objetivo_principal")
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
    goal: str,
    current_wealth: float | None,
    target_wealth: float | None,
    notes: str,
) -> dict[str, Any]:
    profile = default_user_profile()
    profile["nome"] = name.strip().title()
    profile["renda_mensal"] = income
    profile["sem_renda"] = income in (None, 0)
    profile["desempregado"] = income in (None, 0) and not income_source.strip()
    profile["fonte_renda"] = income_source.strip()
    profile["perfil_investidor"] = investor_style
    profile["aceita_risco"] = investor_style != "Conservador"
    profile["gastos_mensais"] = spending
    profile["tem_gastos"] = has_spending
    profile["objetivo_principal"] = goal.strip()
    profile["patrimonio_atual"] = current_wealth
    profile["meta_patrimonial"] = target_wealth
    profile["observacoes"] = notes.strip()
    profile["perfil_pronto"] = True
    return profile


def goal_progress(profile: dict[str, Any]) -> tuple[float | None, float | None, int]:
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


def log_event(event_name: str, payload: dict[str, Any] | None = None) -> None:
    event_payload = payload or {}
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "event": event_name,
        "payload": event_payload,
    }
    try:
        with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Failed to write event log: %s", exc)


def serialize_transactions(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    copy = dataframe.copy()
    copy["data"] = copy["data"].astype(str)
    return copy.to_dict(orient="records")


def deserialize_transactions(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return empty_transactions()
    dataframe = pd.DataFrame(records)
    return normalize_transactions(dataframe)


def load_persistent_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def save_persistent_state(state: dict[str, Any]) -> bool:
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        logger.warning("Failed to save persistent state: %s", exc)
        return False


def build_persisted_snapshot(session_state: Any) -> dict[str, Any]:
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


def get_known_assets(products: list[dict[str, Any]]) -> set[str]:
    assets = set()
    for product in products:
        name = str(product.get("nome", "")).strip()
        if name:
            assets.add(name.lower())
        ticker_match = re.findall(r"\(([^)]+)\)", name)
        for ticker in ticker_match:
            assets.add(ticker.strip().lower())
    return assets


def detect_unknown_assets(user_text: str, known_assets: set[str]) -> list[str]:
    explicit_tickers = re.findall(r"\b[A-Z]{2,6}\b", user_text)
    return [token for token in explicit_tickers if token.lower() not in known_assets]


PRICE_SYMBOL_ALIASES = {
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
    "solana": "SOL-USD",
    "sol": "SOL-USD",
    "xrp": "XRP-USD",
    "doge": "DOGE-USD",
    "voo": "VOO",
    "qqq": "QQQ",
    "vt": "VT",
    "gld": "GLD",
    "spy": "SPY",
    "ivv": "IVV",
    "aapl": "AAPL",
    "msft": "MSFT",
    "nvda": "NVDA",
    "tsla": "TSLA",
}


def is_price_query(user_text: str) -> bool:
    lower = user_text.lower()
    keywords = [
        "preço",
        "preco",
        "cotação",
        "cotacao",
        "quanto está",
        "valor agora",
        "price",
        "quote",
        "how much is",
        "current price",
    ]
    return any(keyword in lower for keyword in keywords)


def extract_market_symbols(user_text: str, known_assets: set[str]) -> list[str]:
    lower = user_text.lower()
    symbols: list[str] = []

    for alias, mapped in PRICE_SYMBOL_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            symbols.append(mapped)

    explicit_tickers = re.findall(r"\b[A-Z]{2,6}\b", user_text)
    for ticker in explicit_tickers:
        ticker_upper = ticker.upper()
        if (
            ticker.lower() in known_assets
            or ticker_upper in PRICE_SYMBOL_ALIASES.values()
        ):
            if ticker_upper in {"BTC", "ETH", "SOL", "XRP", "DOGE"}:
                ticker_upper = f"{ticker_upper}-USD"
            symbols.append(ticker_upper)

    deduped = []
    for symbol in symbols:
        if symbol not in deduped:
            deduped.append(symbol)
    return deduped[:6]


def fetch_market_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    if not symbols:
        return {}

    try:
        response = requests.get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": ",".join(symbols)},
            timeout=8,
        )
        if response.status_code != 200:
            return {}
        results = response.json().get("quoteResponse", {}).get("result", [])
    except (requests.RequestException, ValueError):
        return {}

    quotes: dict[str, dict[str, Any]] = {}
    for item in results:
        symbol = str(item.get("symbol", "")).upper()
        price = item.get("regularMarketPrice")
        currency = item.get("currency", "")
        change_pct = item.get("regularMarketChangePercent")
        if symbol and price is not None:
            quotes[symbol] = {
                "price": float(price),
                "currency": str(currency),
                "change_pct": float(change_pct) if change_pct is not None else None,
            }
    return quotes


def format_market_snapshot(quotes: dict[str, dict[str, Any]], language: str) -> str:
    texts = get_texts(language)
    if not quotes:
        return texts["price_unavailable"]

    lines = [texts["price_snapshot_title"]]
    for symbol, data in quotes.items():
        currency = data.get("currency", "")
        price = data.get("price", 0.0)
        change_pct = data.get("change_pct")
        if change_pct is None:
            lines.append(f"- {symbol}: {price:.2f} {currency}".strip())
        else:
            lines.append(
                f"- {symbol}: {price:.2f} {currency} ({change_pct:+.2f}%)".strip()
            )
    return "\n".join(lines)


def normalize_transactions(dataframe: pd.DataFrame) -> pd.DataFrame:
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
    top_categories = by_category.head(5).to_dict(orient="records")

    products_view = []
    for item in products[:15]:
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
            "objetivo_principal": profile.get("objetivo_principal"),
            "patrimonio_atual": profile.get("patrimonio_atual"),
            "meta_patrimonial": profile.get("meta_patrimonial"),
            "valor_faltante_meta": (
                max(
                    float(profile.get("meta_patrimonial") or 0.0)
                    - float(profile.get("patrimonio_atual") or 0.0),
                    0.0,
                )
                if profile.get("meta_patrimonial") not in (None, "")
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
    messages: list[dict[str, str]], limit: int = 8
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
    if language == "en":
        instructions = (
            "Reply in English. Keep the conversation natural, warm, playful, and continuous. "
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
    else:
        instructions = (
            "Responda em português do Brasil, com conversa natural, humana, leve e brincalhona na medida certa. "
            "Aja como um consultor financeiro experiente: monte carteiras, explique taxas, impostos e decisões de alocação de forma prática. "
            "Responda direto ao ponto, com critério e confiança, sem soar genérico. "
            "Não use menus, listas engessadas ou tom robótico. "
            "Pode usar humor leve e acolhimento quando fizer sentido, sem infantilizar. "
            "Se a pessoa disser que está desempregada ou sem renda, não insista em pedir renda logo depois; "
            "oriente para gastos essenciais, estabilidade e próximos passos realistas. "
            "Este assistente é Brasil-first: priorize produtos, regras e taxação do Brasil. "
            "Se a pessoa pedir jurisdições fora do Brasil, explique o limite de escopo e traga para o contexto brasileiro. "
            "Use o contexto fornecido apenas para se orientar e nunca invente fatos."
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": instructions},
        {
            "role": "system",
            "content": (
                "CONTEXTO ESTRUTURADO DO USUÁRIO:\n"
                f"{context}\n\n"
                "Use esse contexto para personalizar a resposta com segurança."
            ),
        },
    ]
    if market_snapshot:
        messages.append(
            {
                "role": "system",
                "content": (
                    "DADOS RECENTES DE PREÇO PARA USAR NA RESPOSTA (se relevantes):\n"
                    f"{market_snapshot}"
                ),
            }
        )
    if finance_knowledge_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "BASE DE CONHECIMENTO FINANCEIRA CURADA (usar quando relevante):\n"
                    f"{finance_knowledge_context}"
                ),
            }
        )
    messages.extend(conversation_messages)
    messages.append({"role": "user", "content": user_text})
    return messages


def fallback_offline_response(user_text: str, language: str) -> str:
    texts = get_texts(language)
    lower = user_text.lower().strip()
    if any(
        phrase in lower
        for phrase in [
            "oi",
            "olá",
            "ola",
            "bom dia",
            "boa tarde",
            "boa noite",
            "tudo bem",
            "hello",
            "hi",
            "how are you",
        ]
    ):
        return texts["fallback_greeting"]
    return texts["fallback_general"]


def extract_profile_updates(user_text: str, profile: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    text = user_text.strip()
    lower = text.lower()

    user_name = extract_user_name(text)
    if user_name and not profile.get("nome"):
        updates["nome"] = user_name

    income_match = re.search(
        r"(?:renda mensal|ganho por mês|monthly income|i make)\D*(\d+[\d\.,]*)",
        lower,
    )
    if income_match:
        income_raw = income_match.group(1).replace(".", "").replace(",", ".")
        try:
            updates["renda_mensal"] = float(income_raw)
            updates["sem_renda"] = False
            if not profile.get("fonte_renda"):
                updates["fonte_renda"] = "salário"
        except ValueError:
            pass

    if any(
        term in lower
        for term in [
            "desempregado",
            "desempregada",
            "unemployed",
            "sem emprego",
            "out of work",
        ]
    ):
        updates["desempregado"] = True
        updates["sem_renda"] = True
        updates["renda_mensal"] = 0.0
        updates["fonte_renda"] = "sem renda"

    if any(
        term in lower
        for term in ["sem renda", "nenhuma renda", "no income", "without income"]
    ):
        updates["sem_renda"] = True
        updates["renda_mensal"] = 0.0
        if not updates.get("fonte_renda"):
            updates["fonte_renda"] = "sem renda"

    if any(term in lower for term in ["salário", "salario", "salary"]):
        updates["fonte_renda"] = "salário"
    elif any(term in lower for term in ["freela", "freelance", "freelas"]):
        updates["fonte_renda"] = "freelance"
    elif any(term in lower for term in ["negócio", "negocio", "business"]):
        updates["fonte_renda"] = "negócio próprio"

    goal_match = re.search(
        r"(?:quero|meu objetivo é|my goal is|i want to)\s+(.+)", text, re.I
    )
    if goal_match:
        updates["objetivo_principal"] = goal_match.group(1).strip().rstrip(".?!")

    if any(
        term in lower
        for term in ["conservador", "conservative", "baixo risco", "low risk"]
    ):
        updates["perfil_investidor"] = "Conservador"
        updates["aceita_risco"] = False
    elif any(term in lower for term in ["moderado", "moderate"]):
        updates["perfil_investidor"] = "Moderado"
        updates["aceita_risco"] = True
    elif any(
        term in lower for term in ["arrojado", "aggressive", "alto risco", "high risk"]
    ):
        updates["perfil_investidor"] = "Arrojado"
        updates["aceita_risco"] = True

    return updates


def format_profile_summary(profile: dict[str, Any], language: str) -> str:
    labels = {
        "pt": {
            "nome": "Nome",
            "fonte_renda": "Fonte",
            "renda_mensal": "Renda",
            "sem_renda": "Status",
            "perfil_investidor": "Perfil",
            "objetivo_principal": "Objetivo",
            "patrimonio_atual": "Patrimônio",
            "meta_patrimonial": "Meta",
        },
        "en": {
            "nome": "Name",
            "fonte_renda": "Source",
            "renda_mensal": "Income",
            "sem_renda": "Status",
            "perfil_investidor": "Profile",
            "objetivo_principal": "Goal",
            "patrimonio_atual": "Net worth",
            "meta_patrimonial": "Target",
        },
    }

    parts = []
    for key in [
        "nome",
        "fonte_renda",
        "renda_mensal",
        "sem_renda",
        "perfil_investidor",
        "objetivo_principal",
        "patrimonio_atual",
        "meta_patrimonial",
    ]:
        value = profile.get(key)
        if value in (None, "", []):
            continue
        label = labels[language][key]
        if key == "renda_mensal":
            parts.append(f"{label}: {value:,.2f}")
        elif key in {"patrimonio_atual", "meta_patrimonial"}:
            parts.append(f"{label}: {float(value):,.2f}")
        elif key == "sem_renda" and value:
            parts.append(f"{label}: {'sem renda' if language == 'pt' else 'no income'}")
        elif key != "sem_renda":
            parts.append(f"{label}: {value}")
    return " • ".join(parts)


def profile_completion(profile: dict[str, Any]) -> int:
    score = 0
    if profile.get("objetivo_principal"):
        score += 1
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
    return int((score / 6) * 100)


def format_update_fields(profile_updates: dict[str, Any], language: str) -> str:
    labels = {
        "pt": {
            "nome": "nome",
            "renda_mensal": "renda",
            "fonte_renda": "fonte de renda",
            "sem_renda": "status de renda",
            "desempregado": "situação profissional",
            "perfil_investidor": "perfil",
            "objetivo_principal": "objetivo",
            "patrimonio_atual": "patrimônio",
            "meta_patrimonial": "meta",
        },
        "en": {
            "nome": "name",
            "renda_mensal": "income",
            "fonte_renda": "income source",
            "sem_renda": "income status",
            "desempregado": "work status",
            "perfil_investidor": "profile",
            "objetivo_principal": "goal",
            "patrimonio_atual": "net worth",
            "meta_patrimonial": "target",
        },
    }
    return ", ".join(labels[language].get(key, key) for key in profile_updates.keys())


def next_natural_question(
    profile: dict[str, Any], language: str, has_transactions: bool, chat_mode: str
) -> str:
    return ""


def build_consultant_welcome(profile: dict[str, Any], language: str) -> str:
    """Build a personalised welcome that acknowledges the user's profile."""
    name = profile.get("nome", "")
    goal = profile.get("objetivo_principal", "")
    investor = profile.get("perfil_investidor", "")
    renda = profile.get("renda_mensal")
    sem_renda = profile.get("sem_renda", False)

    if language == "en":
        greeting = f"Hey {name}! " if name else "Hey! "
        lines = [
            greeting
            + "Your profile is set. I'm ready to act as your personal financial consultant — no fluff."
        ]
        if goal:
            lines.append(
                f"Your main goal: **{goal}**. That's where we'll keep our focus."
            )
        if investor:
            lines.append(
                f"Investor style noted: **{investor}**. I'll calibrate my recommendations accordingly."
            )
        if sem_renda:
            lines.append(
                "I see you're not relying on income right now — I'll prioritise stability and practical next steps."
            )
        elif renda:
            lines.append(
                f"With **R$ {renda:,.0f}/mo** on hand, let's make the most of it."
            )
        lines.append("What do you want to tackle first?")
        return "\n\n".join(lines)

    greeting = f"Olá, {name}! " if name else "Olá! "
    lines = [
        greeting
        + "Perfil configurado. Agora posso falar como seu consultor financeiro — direto ao ponto, sem rodeios."
    ]
    if goal:
        lines.append(f"Seu objetivo principal: **{goal}**. É nisso que vamos focar.")
    if investor:
        lines.append(
            f"Perfil de investidor anotado: **{investor}**. Vou calibrar as recomendações de acordo."
        )
    if sem_renda:
        lines.append(
            "Vi que você está sem renda no momento — vou priorizar estabilidade e próximos passos práticos."
        )
    elif renda:
        lines.append(
            f"Com **R$ {renda:,.0f}/mês** disponível, dá pra trabalhar bem. Vamos aproveitar isso."
        )
    lines.append("O que você quer resolver primeiro?")
    return "\n\n".join(lines)


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
    answer = response_text.strip()

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
                "desempregado",
                "desempregada",
                "sem renda",
                "unemployed",
                "no income",
            ]
        ):
            answer += "\n\n" + texts["unemployment_support"]
            answer += "\n\n" + texts["no_income_prompt"]

    if unknown_assets:
        unknown_str = ", ".join(unknown_assets)
        answer += "\n\n" + texts["unknown_assets"].format(assets=unknown_str)

    if any(
        keyword in lower
        for keyword in [
            "etf",
            "ação",
            "acoes",
            "stock",
            "cripto",
            "bitcoin",
            "ethereum",
        ]
    ):
        answer += "\n\n" + texts["risk_warning"]

    if profile.get("perfil_investidor") and any(
        keyword in lower for keyword in ["invest", "investment", "investimento"]
    ):
        answer += "\n\n" + texts["investor_context"].format(
            profile=profile.get("perfil_investidor")
        )

    if rate_limit_hit:
        answer += "\n\n" + texts["rate_limit_notice"]

    return answer


def call_groq(messages: list[dict[str, str]]) -> tuple[str | None, bool]:
    if not GROQ_API_KEY:
        return None, False

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7,
    }
    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 429:
            return None, True
        if response.status_code != 200:
            try:
                error_message = response.json().get("error", {}).get("message", "")
            except ValueError:
                error_message = response.text
            rate_limit_hit = (
                "rate limit" in error_message.lower()
                or "token" in error_message.lower()
            )
            return None, rate_limit_hit
        data = response.json()
        return str(data["choices"][0]["message"]["content"]), False
    except (requests.RequestException, KeyError, IndexError):
        return None, False


def call_ollama(messages: list[dict[str, str]]) -> str | None:
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
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    st.set_page_config(page_title="Pluto Finance AI", page_icon="🪐", layout="wide")
    st.markdown(
        """
        <style>
            .block-container {padding-top: 1.2rem; max-width: 96vw !important; width: 96vw !important;}
            .stChatFloatingInputContainer {bottom: 1rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(HIDE_STREAMLIT_CHROME, unsafe_allow_html=True)

    if "state_loaded" not in st.session_state:
        st.session_state.state_loaded = False

    if not st.session_state.state_loaded:
        persisted = load_persistent_state()
        if persisted:
            try:
                st.session_state.language = persisted.get("language", "pt")
                st.session_state.chat_mode = persisted.get("chat_mode", "guided")
                st.session_state.user_profile = persisted.get(
                    "user_profile", default_user_profile()
                )
                st.session_state.messages = persisted.get("messages", [])
                st.session_state.user_transactions = deserialize_transactions(
                    persisted.get("user_transactions", [])
                )
                st.session_state.rate_limit_notice = ""
                st.session_state.feedback = {}
                st.session_state.feedback_notice = ""
                st.session_state.state_restore_notice = "ok"
                st.session_state.profile_ready = profile_is_ready(
                    st.session_state.user_profile
                )
                log_event(
                    "state_restored", {"messages": len(st.session_state.messages)}
                )
            except Exception:
                st.session_state.state_restore_notice = "error"
                log_event("state_restore_error")
        st.session_state.state_loaded = True

    if "language" not in st.session_state:
        st.session_state.language = "pt"
    if "chat_mode" not in st.session_state:
        st.session_state.chat_mode = "guided"
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = default_user_profile()
    if "user_transactions" not in st.session_state:
        st.session_state.user_transactions = empty_transactions()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "rate_limit_notice" not in st.session_state:
        st.session_state.rate_limit_notice = ""
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}
    if "feedback_notice" not in st.session_state:
        st.session_state.feedback_notice = ""
    if "state_restore_notice" not in st.session_state:
        st.session_state.state_restore_notice = ""
    if "profile_ready" not in st.session_state:
        st.session_state.profile_ready = profile_is_ready(st.session_state.user_profile)

    use_english = st.toggle(
        "Responder em inglês / Reply in English",
        value=st.session_state.language == "en",
    )
    language = "en" if use_english else "pt"
    st.session_state.language = language
    texts = get_texts(language)

    st.title("🪐 Pluto Finance AI")
    st.caption(texts["caption"])
    st.info(texts["brazil_focus_notice"])

    if st.session_state.state_restore_notice == "ok":
        st.success(texts["state_restored"])
        st.session_state.state_restore_notice = ""
    elif st.session_state.state_restore_notice == "error":
        st.warning(texts["state_restore_error"])
        st.session_state.state_restore_notice = ""

    products = load_products()
    history = load_history()
    tax_knowledge = load_tax_knowledge_data()
    system_prompt = extract_system_prompt()
    ollama_ready = check_ollama_health()

    if not st.session_state.profile_ready:
        st.markdown(
            """
            <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                        border-radius:16px;padding:2rem 2.5rem 1.5rem 2.5rem;margin-bottom:1.5rem;
                        border:1px solid #0f3460;">
              <h2 style="margin:0 0 .3rem 0;color:#e2e8f0;">🪐 Pluto Finance AI</h2>
              <p style="margin:0;color:#94a3b8;font-size:.95rem;">
                Preencha o perfil uma vez — o Pluto libera o chat já sabendo quem você é e o que quer.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        style_options = [
            ("Conservador", texts["intake_profile_conservative"]),
            ("Moderado", texts["intake_profile_moderate"]),
            ("Arrojado", texts["intake_profile_aggressive"]),
        ]
        style_labels = [label for _, label in style_options]
        style_lookup = {label: value for value, label in style_options}

        with st.form("profile_intake_form", clear_on_submit=False):
            st.markdown("#### Identificação")
            name = st.text_input(
                texts["intake_name"] + " *",
                value=st.session_state.user_profile.get("nome", ""),
                placeholder="Como o Pluto deve te chamar?",
            )

            st.markdown("---")
            st.markdown("#### Renda")
            col_r1, col_r2 = st.columns([1, 2])
            with col_r1:
                has_income = st.checkbox(
                    texts["intake_has_income"],
                    value=st.session_state.user_profile.get("renda_mensal")
                    not in (None, 0, "")
                    or not st.session_state.user_profile.get("sem_renda", False),
                )
            with col_r2:
                income_source = st.text_input(
                    texts["intake_income_source"],
                    value=st.session_state.user_profile.get("fonte_renda", ""),
                    placeholder="Ex: salário, freela, negócio próprio",
                )
            if has_income:
                income = st.number_input(
                    texts["intake_income"],
                    min_value=0.0,
                    value=float(
                        st.session_state.user_profile.get("renda_mensal") or 0.0
                    ),
                    step=100.0,
                    format="%.2f",
                )
            else:
                income = 0.0

            st.markdown("---")
            st.markdown("#### Perfil e Gastos")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                investor_style_label = st.selectbox(
                    texts["intake_profile"] + " *",
                    options=style_labels,
                    index=style_labels.index(
                        {
                            "Conservador": texts["intake_profile_conservative"],
                            "Moderado": texts["intake_profile_moderate"],
                            "Arrojado": texts["intake_profile_aggressive"],
                        }.get(
                            st.session_state.user_profile.get("perfil_investidor")
                            or "Moderado",
                            texts["intake_profile_moderate"],
                        )
                    ),
                )
            with col_p2:
                has_spending = st.checkbox(
                    texts["intake_has_spending"],
                    value=st.session_state.user_profile.get("tem_gastos") is not False,
                )
                if has_spending:
                    spending = st.number_input(
                        texts["intake_spending"],
                        min_value=0.0,
                        value=float(
                            st.session_state.user_profile.get("gastos_mensais") or 0.0
                        ),
                        step=100.0,
                        format="%.2f",
                    )
                else:
                    spending = 0.0

            st.markdown("---")
            st.markdown("#### Objetivo e Meta")
            goal = st.text_area(
                texts["intake_goal"] + " *",
                value=st.session_state.user_profile.get("objetivo_principal", ""),
                height=90,
                placeholder="Ex: montar reserva de emergência, quitar dívidas, investir para aposentadoria…",
            )
            wealth_col1, wealth_col2 = st.columns(2)
            with wealth_col1:
                current_wealth = st.number_input(
                    texts["intake_current_wealth"],
                    min_value=0.0,
                    value=float(
                        st.session_state.user_profile.get("patrimonio_atual") or 0.0
                    ),
                    step=500.0,
                    format="%.2f",
                )
            with wealth_col2:
                target_wealth = st.number_input(
                    texts["intake_target_wealth"],
                    min_value=0.0,
                    value=float(
                        st.session_state.user_profile.get("meta_patrimonial") or 0.0
                    ),
                    step=1000.0,
                    format="%.2f",
                )
            notes = st.text_area(
                texts["intake_notes"],
                value=st.session_state.user_profile.get("observacoes", ""),
                height=60,
                placeholder="Algo mais que o Pluto deve saber sobre você?",
            )

            st.markdown(" ")
            submit = st.form_submit_button(
                texts["intake_submit"],
                use_container_width=True,
                type="primary",
            )

        if submit:
            stored_profile = apply_profile_form_submission(
                name=name,
                income=income if has_income else None,
                income_source=income_source,
                investor_style=style_lookup[investor_style_label],
                spending=spending if has_spending else None,
                has_spending=has_spending,
                goal=goal,
                current_wealth=current_wealth if current_wealth > 0 else None,
                target_wealth=target_wealth if target_wealth > 0 else None,
                notes=notes,
            )
            if (
                not stored_profile["nome"]
                or not stored_profile["perfil_investidor"]
                or not stored_profile["objetivo_principal"]
            ):
                st.warning(texts["intake_missing_warning"])
            else:
                if (
                    not stored_profile["renda_mensal"]
                    and not stored_profile["sem_renda"]
                ):
                    stored_profile["sem_renda"] = True
                st.session_state.user_profile = stored_profile
                st.session_state.profile_ready = True
                welcome_msg = build_consultant_welcome(stored_profile, language)
                st.session_state.messages = [
                    {"role": "assistant", "content": welcome_msg}
                ]
                st.session_state.rate_limit_notice = ""
                log_event(
                    "profile_form_submitted", {"fields": list(stored_profile.keys())}
                )
                save_persistent_state(build_persisted_snapshot(st.session_state))
                st.rerun()

        st.stop()

    completion = profile_completion(st.session_state.user_profile)
    interaction_count = len(
        [m for m in st.session_state.messages if m.get("role") == "user"]
    )
    transaction_count = int(len(st.session_state.user_transactions))

    # ── Mini Profile Dashboard ────────────────────────────────────────────
    profile = st.session_state.user_profile
    _name = profile.get("nome", "—")
    _style = profile.get("perfil_investidor", "—")
    _goal = profile.get("objetivo_principal", "—")
    _renda_raw = profile.get("renda_mensal")
    _sem_renda = profile.get("sem_renda", False)
    if _sem_renda or not _renda_raw:
        _renda_str = "Sem renda" if language == "pt" else "No income"
    else:
        _renda_str = f"R$ {float(_renda_raw):,.0f}/mês"
    _gastos_raw = profile.get("gastos_mensais")
    _gastos_str = f"R$ {float(_gastos_raw):,.0f}/mês" if _gastos_raw else "—"
    _current_wealth, _target_wealth, _goal_progress = goal_progress(profile)
    _missing = None
    if _current_wealth is not None and _target_wealth is not None:
        _missing = max(_target_wealth - _current_wealth, 0.0)
    _bar_w = completion
    _txn_count = transaction_count
    _inter_count = interaction_count

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
                    border-radius:14px;padding:1.1rem 1.5rem;margin-bottom:1rem;
                    border:1px solid #334155;display:flex;flex-wrap:wrap;gap:1.2rem;
                    align-items:center;">
          <div style="flex:1 1 120px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Nome</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{_name}</div>
          </div>
          <div style="flex:1 1 120px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Perfil</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{_style}</div>
          </div>
          <div style="flex:1 1 150px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Renda</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{_renda_str}</div>
          </div>
                    <div style="flex:1 1 150px;">
                        <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_current_label']}</div>
                        <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {_current_wealth:,.0f}' if _current_wealth is not None else '—')}</div>
                    </div>
                    <div style="flex:1 1 150px;">
                        <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_target_label']}</div>
                        <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {_target_wealth:,.0f}' if _target_wealth is not None else '—')}</div>
                    </div>
                    <div style="flex:1 1 150px;">
                        <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['wealth_missing_label']}</div>
                        <div style="color:#f1f5f9;font-weight:600;font-size:.95rem;">{(f'R$ {_missing:,.0f}' if _missing is not None else '—')}</div>
                    </div>
          <div style="flex:2 1 200px;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Objetivo</div>
            <div style="color:#f1f5f9;font-size:.88rem;">{_goal[:60]}{"…" if len(_goal) > 60 else ""}</div>
          </div>
          <div style="flex:1 1 100px;text-align:right;">
                        <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">{texts['intake_goal_progress']}</div>
            <div style="background:#1e293b;border-radius:99px;height:6px;margin-top:4px;">
                            <div style="background:#38bdf8;width:{_goal_progress if _target_wealth else _bar_w}%;height:6px;border-radius:99px;"></div>
            </div>
                        <div style="color:#38bdf8;font-size:.78rem;margin-top:2px;">{_goal_progress if _target_wealth else _bar_w}%</div>
          </div>
          <div style="flex:1 1 80px;text-align:center;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Msgs</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:1.1rem;">{_inter_count}</div>
          </div>
          <div style="flex:1 1 80px;text-align:center;">
            <div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;">Transações</div>
            <div style="color:#f1f5f9;font-weight:600;font-size:1.1rem;">{_txn_count}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Edit profile button
    if st.button(texts["edit_profile"], key="btn_edit_profile"):
        st.session_state.profile_ready = False
        st.rerun()

    with st.expander(texts["csv_title"], expanded=False):
        st.caption(texts["csv_caption"])
        uploaded_file = st.file_uploader(
            texts["upload_label"], type=["csv"], help=texts["upload_help"]
        )
        if uploaded_file is not None:
            try:
                uploaded_transactions = pd.read_csv(uploaded_file)
                st.session_state.user_transactions = normalize_transactions(
                    uploaded_transactions
                )
                st.success(texts["upload_success"])
                log_event(
                    "transactions_uploaded",
                    {"rows": int(len(st.session_state.user_transactions))},
                )
                save_persistent_state(build_persisted_snapshot(st.session_state))
            except Exception:
                st.error(texts["upload_error"])
                log_event("transactions_upload_error")

    profile_summary = format_profile_summary(st.session_state.user_profile, language)
    if profile_summary:
        st.caption(f"{texts['profile_summary']}: {profile_summary}")
    else:
        st.caption(f"{texts['profile_summary']}: {texts['profile_empty']}")

    if not st.session_state.messages:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": build_consultant_welcome(
                    st.session_state.user_profile, language
                ),
            }
        ]

    if st.session_state.rate_limit_notice:
        st.warning(st.session_state.rate_limit_notice)
    if st.session_state.feedback_notice:
        st.success(st.session_state.feedback_notice)
        st.session_state.feedback_notice = ""

    last_assistant_index = max(
        (
            index
            for index, message in enumerate(st.session_state.messages)
            if message["role"] == "assistant"
        ),
        default=-1,
    )

    for index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and index == last_assistant_index:
                st.caption(texts["feedback_title"])
                fb_key = f"feedback_{index}"
                already_sent = st.session_state.feedback.get(f"{fb_key}_sent", False)
                if not already_sent:
                    fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 4])
                    with fb_col1:
                        thumb_up = st.button(
                            texts["feedback_positive"], key=f"fb_up_{index}"
                        )
                    with fb_col2:
                        thumb_down = st.button(
                            texts["feedback_negative"], key=f"fb_down_{index}"
                        )
                    if thumb_up or thumb_down:
                        st.session_state.feedback[f"{fb_key}_vote"] = (
                            "positive" if thumb_up else "negative"
                        )
                        st.session_state.feedback[f"{fb_key}_show_form"] = True
                        st.rerun()
                    if st.session_state.feedback.get(f"{fb_key}_show_form"):
                        with st.form(key=f"fb_form_{index}", clear_on_submit=True):
                            rating = st.slider(
                                texts["feedback_rating_label"],
                                min_value=1,
                                max_value=5,
                                value=(
                                    4
                                    if st.session_state.feedback.get(f"{fb_key}_vote")
                                    == "positive"
                                    else 2
                                ),
                                key=f"fb_rating_{index}",
                            )
                            comment = st.text_area(
                                texts["feedback_comment_label"],
                                placeholder=texts["feedback_comment_placeholder"],
                                height=80,
                                key=f"fb_comment_{index}",
                            )
                            if st.form_submit_button(texts["feedback_submit"]):
                                vote = st.session_state.feedback.get(
                                    f"{fb_key}_vote", "positive"
                                )
                                st.session_state.feedback[fb_key] = vote
                                st.session_state.feedback[f"{fb_key}_rating"] = rating
                                st.session_state.feedback[f"{fb_key}_comment"] = comment
                                st.session_state.feedback[f"{fb_key}_sent"] = True
                                st.session_state.feedback_notice = texts[
                                    "feedback_saved"
                                ]
                                log_event(
                                    "feedback_submitted",
                                    {
                                        "message_index": index,
                                        "vote": vote,
                                        "rating": rating,
                                        "comment": comment[:300] if comment else "",
                                    },
                                )
                                save_persistent_state(
                                    build_persisted_snapshot(st.session_state)
                                )
                                st.rerun()
                else:
                    vote_label = (
                        texts["feedback_positive"]
                        if st.session_state.feedback.get(f"{fb_key}_vote") == "positive"
                        else texts["feedback_negative"]
                    )
                    rating_val = st.session_state.feedback.get(f"{fb_key}_rating", "")
                    comment_val = st.session_state.feedback.get(f"{fb_key}_comment", "")
                    summary = f"{vote_label} {rating_val}/5"
                    if comment_val:
                        summary += f" · _{comment_val[:60]}{'…' if len(comment_val) > 60 else ''}_"
                    st.caption(f"{texts['feedback_saved']} {summary}")

    user_text = st.chat_input(texts["chat_placeholder"])
    if not user_text:
        return

    log_event(
        "user_message_received",
        {
            "language": language,
            "chat_mode": st.session_state.chat_mode,
            "message_length": len(user_text),
        },
    )

    profile_updates = extract_profile_updates(user_text, st.session_state.user_profile)
    if profile_updates:
        st.session_state.user_profile.update(profile_updates)
        log_event("profile_updated", {"fields": list(profile_updates.keys())})

    # Auto-detect and register transactions from natural language
    transaction_notice = ""
    if is_transaction_message(user_text):
        txn = extract_transaction_from_message(user_text)
        if txn:
            txn_row = pd.DataFrame([txn])
            txn_row["data"] = pd.to_datetime(txn_row["data"], errors="coerce")
            txn_row["valor"] = pd.to_numeric(txn_row["valor"], errors="coerce").fillna(
                0.0
            )
            st.session_state.user_transactions = pd.concat(
                [st.session_state.user_transactions, txn_row], ignore_index=True
            )
            log_event("transaction_recorded", txn)
            tipo_label = "Entrada" if txn["tipo"] == "entrada" else "Saída"
            transaction_notice = texts["transaction_recorded"].format(
                tipo=tipo_label,
                valor=txn["valor"],
                categoria=txn["categoria"],
                data=txn["data"],
            )

    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    if transaction_notice:
        st.info(transaction_notice)
        st.caption(texts["transaction_recorded_caption"])

    known_assets = get_known_assets(products)
    unknown_assets = detect_unknown_assets(user_text, known_assets)

    market_snapshot = ""
    if is_price_query(user_text):
        symbols = extract_market_symbols(user_text, known_assets)
        quotes = fetch_market_quotes(symbols)
        market_snapshot = format_market_snapshot(quotes, language)

    context = build_context(
        st.session_state.user_profile,
        st.session_state.user_transactions,
        products,
        history,
    )
    finance_knowledge_context = build_finance_knowledge_context(
        user_text=user_text,
        profile=st.session_state.user_profile,
        products=products,
        tax_knowledge=tax_knowledge,
        language=language,
    )
    conversation_messages = build_recent_messages(st.session_state.messages[:-1])
    llm_messages = build_llm_messages(
        system_prompt=system_prompt,
        context=context,
        user_text=user_text,
        conversation_messages=conversation_messages,
        language=language,
        market_snapshot=market_snapshot,
        finance_knowledge_context=finance_knowledge_context,
    )

    answer, rate_limit_hit = call_groq(llm_messages)
    st.session_state.rate_limit_notice = (
        texts["rate_limit_notice"] if rate_limit_hit else ""
    )
    if rate_limit_hit:
        log_event("groq_rate_limited")

    if not answer and ollama_ready:
        answer = call_ollama(llm_messages)
        if answer:
            log_event("answer_source", {"source": "ollama"})

    if not answer:
        answer = fallback_offline_response(user_text, language)
        log_event("answer_source", {"source": "fallback"})
    elif not rate_limit_hit:
        log_event("answer_source", {"source": "groq"})

    answer = apply_post_response_validation(
        response_text=answer,
        profile=st.session_state.user_profile,
        user_text=user_text,
        unknown_assets=unknown_assets,
        language=language,
        rate_limit_hit=rate_limit_hit,
        profile_updates=profile_updates,
    )

    if is_price_query(user_text) and market_snapshot:
        if (
            "snapshot" not in answer.lower()
            and "cotação" not in answer.lower()
            and "quote" not in answer.lower()
        ):
            answer += "\n\n" + market_snapshot

    followup_question = next_natural_question(
        st.session_state.user_profile,
        language,
        has_transactions=not st.session_state.user_transactions.empty,
        chat_mode="quick",
    )
    if followup_question and followup_question.lower() not in answer.lower():
        answer += "\n\n" + followup_question

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)

    if not save_persistent_state(build_persisted_snapshot(st.session_state)):
        st.warning(texts["state_save_error"])
        log_event("state_save_error")


if __name__ == "__main__":
    main()
