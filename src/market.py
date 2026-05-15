"""Market data and asset management module."""

from __future__ import annotations

import re
from typing import Any

import requests

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


def get_known_assets(products: list[dict[str, Any]]) -> set[str]:
    """Extract all known asset tickers from product catalog."""
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
    """Find asset symbols in user text that are not in the known assets set."""
    explicit_tickers = re.findall(r"\b[A-Z]{2,6}\b", user_text)
    return [token for token in explicit_tickers if token.lower() not in known_assets]


def is_price_query(user_text: str) -> bool:
    """Check if user is asking for price information."""
    lower = user_text.lower()
    keywords = [
        "price",
        "quote",
        "how much is",
        "current price",
    ]
    return any(keyword in lower for keyword in keywords)


def extract_market_symbols(user_text: str, known_assets: set[str]) -> list[str]:
    """Extract market symbols from user text for price queries."""
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
    """Fetch real-time market quotes from Yahoo Finance."""
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
    """Format market quotes as a readable snapshot."""
    # Fallback text if TEXTS not available
    texts_fallback = {
        "en": {
            "price_unavailable": "I couldn't fetch live prices right now. If you want, I can try again in a moment.",
            "price_snapshot_title": "📈 Quick market snapshot",
        }
    }

    texts = texts_fallback.get(language, texts_fallback["en"])

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
