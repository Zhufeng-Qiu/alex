"""
HTTP-based tools for the Briefer agent.

These keep the Lambda lightweight by using direct HTTP calls instead of MCP/Playwright.
"""

import os
from typing import Dict, Any, List

import httpx
from agents import function_tool


ALPHAVANTAGE_ENDPOINT = "https://www.alphavantage.co/query"
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")


def _fetch_alpha_vantage_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Internal helper to fetch quotes from Alpha Vantage."""
    if not symbols:
        return {"success": False, "error": "No symbols provided"}

    if not ALPHAVANTAGE_API_KEY:
        return {"success": False, "error": "ALPHAVANTAGE_API_KEY is not configured"}

    results: Dict[str, Any] = {}

    try:
        with httpx.Client(timeout=10.0) as client:
            for symbol in symbols:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": ALPHAVANTAGE_API_KEY,
                }
                resp = client.get(ALPHAVANTAGE_ENDPOINT, params=params)
                resp.raise_for_status()
                data = resp.json()
                results[symbol] = data
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": True, "raw": results}


@function_tool
def fetch_market_overview() -> Dict[str, Any]:
    """
    Fetch a quick market overview for major US indices.

    Returns:
        A dictionary with basic quote data for S&P 500 (SPY), Nasdaq-100 (QQQ), and Dow (DIA) via their ETFs.
    """
    symbols = ["SPY", "QQQ", "DIA"]
    return _fetch_alpha_vantage_quotes(symbols)


@function_tool
def fetch_ticker_quotes(tickers: str) -> Dict[str, Any]:
    """
    Fetch quote snapshots for a comma-separated list of tickers.

    Args:
        tickers: Comma-separated list of ticker symbols (e.g., "AAPL,NVDA,MSFT").

    Returns:
        Raw Alpha Vantage quote responses for the requested tickers.
    """
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    return _fetch_alpha_vantage_quotes(symbols)

