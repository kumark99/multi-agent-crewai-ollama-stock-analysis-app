"""
news_tools.py – CrewAI tools for fetching stock news and market sentiment.

Tools
─────
  StockNewsTool        →  Latest news via DuckDuckGo News search
  MarketSentimentTool  →  Analyst ratings and broader market opinion
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class StockInput(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol, e.g. AAPL, TSLA")


# ── Zerodha Pulse scraper (used for .NS / .BO Indian stocks) ──────────────────

# Well-known NSE ticker → common name aliases used in article headlines
_NSE_ALIASES: dict[str, list[str]] = {
    "RELIANCE":    ["Reliance"],
    "TCS":         ["TCS", "Tata Consultancy"],
    "INFY":        ["Infosys"],
    "HDFCBANK":    ["HDFC Bank"],
    "ICICIBANK":   ["ICICI Bank"],
    "WIPRO":       ["Wipro"],
    "HINDUNILVR":  ["HUL", "Hindustan Unilever"],
    "KOTAKBANK":   ["Kotak"],
    "SBIN":        ["SBI", "State Bank"],
    "BAJFINANCE":  ["Bajaj Finance"],
    "AXISBANK":    ["Axis Bank"],
    "LT":          ["L&T", "Larsen"],
    "SUNPHARMA":   ["Sun Pharma"],
    "TATAMOTORS":  ["Tata Motors"],
    "TATASTEEL":   ["Tata Steel"],
    "ITC":         ["ITC"],
    "BHARTIARTL":  ["Airtel", "Bharti Airtel"],
    "MARUTI":      ["Maruti"],
    "NTPC":        ["NTPC"],
    "POWERGRID":   ["Power Grid"],
    "ONGC":        ["ONGC"],
    "COALINDIA":   ["Coal India"],
    "INDUSINDBK":  ["IndusInd"],
    "TECHM":       ["Tech Mahindra"],
    "HCLTECH":     ["HCL"],
    "ASIANPAINT":  ["Asian Paints"],
    "ULTRACEMCO":  ["UltraTech"],
    "BAJAJFINSV":  ["Bajaj Finserv"],
    "NESTLEIND":   ["Nestle"],
    "BRITANNIA":   ["Britannia"],
    "DIVISLAB":    ["Divi"],
    "CIPLA":       ["Cipla"],
    "DRREDDY":     ["Dr Reddy"],
    "GRASIM":      ["Grasim"],
    "HINDALCO":    ["Hindalco"],
    "JSWSTEEL":    ["JSW Steel"],
    "INDIGO":      ["IndiGo"],
    "ADANIPORTS":  ["Adani Ports"],
    "ADANIENT":    ["Adani Enterprises"],
    "MRF":         ["MRF"],
    "BAJAJ-AUTO":  ["Bajaj Auto"],
    "HEROMOOCO":   ["Hero MotoCorp"],
    "EICHERMOT":   ["Eicher"],
    "SHRIRAMFIN":  ["Shriram Finance"],
    "DLF":         ["DLF"],
    "VEDL":        ["Vedanta"],
    "NALCO":       ["NALCO"],
    "BPCL":        ["BPCL"],
    "IOC":         ["IOC", "Indian Oil"],
    "HPCL":        ["HPCL"],
    "SWIGGY":      ["Swiggy"],
    "ZOMATO":      ["Zomato"],
    "BSE":         ["BSE"],
    "MCX":         ["MCX"],
}

_PULSE_URL = "https://pulse.zerodha.com/"
_PULSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_zerodha_pulse_news(symbol: str, max_results: int = 12) -> list[dict]:
    """
    Scrape https://pulse.zerodha.com/ and return news articles relevant to the
    given NSE/BSE stock symbol (e.g. RELIANCE.NS, TCS.NS).

    Strategy
    ────────
    1. Strip the exchange suffix (.NS / .BO) to get the base ticker.
    2. Build a list of search terms: base ticker + known alias names.
    3. Scrape the Pulse homepage with requests + BeautifulSoup.
    4. Filter articles whose title contains any of the search terms.
    5. Return structured dicts (title, date, source, summary, url).
    """
    import requests
    from bs4 import BeautifulSoup

    base_ticker = (
        symbol.upper()
        .replace(".NS", "")
        .replace(".BO", "")
        .replace("-EQ", "")
    )

    search_terms: list[str] = [base_ticker] + _NSE_ALIASES.get(base_ticker, [])

    # ── fetch page (try verified SSL first; fall back to unverified on macOS) ──
    import urllib3

    try:
        resp = requests.get(_PULSE_URL, headers=_PULSE_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        # macOS self-signed cert chain issue – retry without verification
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            resp = requests.get(
                _PULSE_URL, headers=_PULSE_HEADERS, timeout=15, verify=False
            )
            resp.raise_for_status()
        except Exception as exc:
            return [{"error": f"Could not reach Zerodha Pulse: {exc}", "source": "Zerodha Pulse"}]
    except Exception as exc:
        return [{"error": f"Could not reach Zerodha Pulse: {exc}", "source": "Zerodha Pulse"}]

    soup = BeautifulSoup(resp.text, "html.parser")
    news_items: list[dict] = []

    # ── locate article containers ────────────────────────────────────────────
    # Zerodha Pulse HTML: <ul id="news-list"> <li class="item"> ...
    articles = (
        soup.select("#news-list li.item")
        or soup.select("li.item")
        or soup.select("#news-list li")
        or soup.select("div.item")
    )

    def _matches(title: str) -> bool:
        tl = title.lower()
        return any(term.lower() in tl for term in search_terms)

    if articles:
        for article in articles:
            link = article.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            if not _matches(title):
                continue
            url = link.get("href", "N/A")

            # Description
            desc_tag = article.find("p")
            description = desc_tag.get_text(strip=True)[:350] if desc_tag else ""

            # Date & source from .sub container
            date_str, source = "N/A", "Zerodha Pulse"
            sub = article.find(
                class_=re.compile(r"\bsub\b|\bmeta\b|\binfo\b", re.I)
            )
            if sub:
                for span in sub.find_all("span"):
                    cls = " ".join(span.get("class", []))
                    text = span.get_text(strip=True)
                    if re.search(r"date|time", cls, re.I):
                        date_str = text
                    elif re.search(r"source|channel|pub", cls, re.I):
                        source = text

            # Fallback: scan all spans for "ago" text
            if date_str == "N/A":
                for span in article.find_all("span"):
                    if "ago" in span.get_text().lower():
                        date_str = span.get_text(strip=True)
                        break

            news_items.append({
                "title": title,
                "date": date_str,
                "source": source,
                "summary": description or "N/A",
                "url": url,
            })
            if len(news_items) >= max_results:
                break

    else:
        # Fallback: scan all <h2> headings directly
        for h2 in soup.find_all("h2"):
            link = h2.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            if not _matches(title):
                continue
            parent = h2.parent
            desc_tag = parent.find("p") if parent else None
            description = desc_tag.get_text(strip=True)[:350] if desc_tag else ""
            news_items.append({
                "title": title,
                "date": "N/A",
                "source": "Zerodha Pulse",
                "summary": description or "N/A",
                "url": link.get("href", "N/A"),
            })
            if len(news_items) >= max_results:
                break

    return news_items


# ── StockNewsTool ─────────────────────────────────────────────────────────────

class StockNewsTool(BaseTool):
    name: str = "Get Stock News"
    description: str = (
        "Fetches the latest news articles related to a stock symbol from the web. "
        "Returns article titles, dates, sources, and summaries."
    )
    args_schema: Type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        try:
            sym_upper = symbol.upper()
            is_indian = sym_upper.endswith(".NS") or sym_upper.endswith(".BO")
            news_items: list[dict] = []

            if is_indian:
                # ── Indian stocks → Zerodha Pulse ─────────────────────────
                news_source = "Zerodha Pulse (pulse.zerodha.com)"
                pulse_results = _fetch_zerodha_pulse_news(sym_upper)

                # If Pulse returned an error or nothing, fall back to DDG
                has_error = (
                    len(pulse_results) == 1
                    and "error" in pulse_results[0]
                )
                if pulse_results and not has_error:
                    news_items = pulse_results
                else:
                    # Fallback: DuckDuckGo with Indian market context
                    from duckduckgo_search import DDGS

                    base = sym_upper.replace(".NS", "").replace(".BO", "")
                    query = (
                        f"{base} NSE stock news earnings results "
                        f"Moneycontrol Economic Times"
                    )
                    news_source = "DuckDuckGo News (fallback)"
                    with DDGS() as ddgs:
                        results = list(ddgs.news(query, max_results=12))
                    for item in results:
                        news_items.append({
                            "title": item.get("title", "N/A"),
                            "date": item.get("date", "N/A"),
                            "source": item.get("source", "N/A"),
                            "summary": item.get("body", "N/A")[:350],
                            "url": item.get("url", "N/A"),
                        })
            else:
                # ── Non-Indian stocks → DuckDuckGo (existing flow) ────────
                from duckduckgo_search import DDGS

                news_source = "DuckDuckGo News"
                query = f"{symbol} stock news earnings analyst"
                with DDGS() as ddgs:
                    results = list(ddgs.news(query, max_results=12))
                for item in results:
                    news_items.append({
                        "title": item.get("title", "N/A"),
                        "date": item.get("date", "N/A"),
                        "source": item.get("source", "N/A"),
                        "summary": item.get("body", "N/A")[:350],
                        "url": item.get("url", "N/A"),
                    })

            return json.dumps(
                {
                    "symbol": sym_upper,
                    "news_source": news_source,
                    "fetched_at": datetime.now().isoformat(),
                    "total_articles": len(news_items),
                    "news": news_items,
                },
                indent=2,
                default=str,
            )

        except ImportError:
            return (
                "Required package not installed. "
                "Run: pip install duckduckgo-search beautifulsoup4"
            )
        except Exception as e:
            return f"Error fetching news for {symbol}: {str(e)}"


# ── MarketSentimentTool ───────────────────────────────────────────────────────

class MarketSentimentTool(BaseTool):
    name: str = "Get Market Sentiment"
    description: str = (
        "Searches for analyst ratings, price target changes, upgrades/downgrades, "
        "and institutional sentiment for a stock symbol."
    )
    args_schema: Type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        try:
            from duckduckgo_search import DDGS

            sym_upper = symbol.upper()
            is_indian = sym_upper.endswith(".NS") or sym_upper.endswith(".BO")

            if is_indian:
                base = sym_upper.replace(".NS", "").replace(".BO", "")
                queries = [
                    f"{base} NSE analyst rating buy sell target price 2025 2026",
                    f"{base} stock outlook brokerage upgrade downgrade "
                    f"Moneycontrol Economic Times NDTV Profit",
                ]
            else:
                queries = [
                    f"{symbol} analyst rating upgrade downgrade 2025 2026",
                    f"{symbol} stock price target institutional investor",
                ]
            sentiment_items = []

            with DDGS() as ddgs:
                for q in queries:
                    results = list(ddgs.text(q, max_results=5))
                    for item in results:
                        sentiment_items.append(
                            {
                                "title": item.get("title", "N/A"),
                                "snippet": item.get("body", "N/A")[:300],
                                "url": item.get("href", item.get("url", "N/A")),
                            }
                        )

            # Also try to get yfinance analyst data
            analyst_data = {}
            try:
                import yfinance as yf

                ticker = yf.Ticker(symbol.upper())
                info = ticker.info
                analyst_data = {
                    "recommendation": info.get("recommendationKey", "N/A"),
                    "target_mean": info.get("targetMeanPrice", "N/A"),
                    "target_low": info.get("targetLowPrice", "N/A"),
                    "target_high": info.get("targetHighPrice", "N/A"),
                    "number_of_analysts": info.get("numberOfAnalystOpinions", "N/A"),
                }
            except Exception:
                pass

            return json.dumps(
                {
                    "symbol": symbol.upper(),
                    "analyst_consensus": analyst_data,
                    "sentiment_sources": sentiment_items[:8],
                    "fetched_at": datetime.now().isoformat(),
                },
                indent=2,
                default=str,
            )

        except ImportError:
            return (
                "duckduckgo-search package is not installed. "
                "Run: pip install duckduckgo-search"
            )
        except Exception as e:
            return f"Error fetching sentiment for {symbol}: {str(e)}"
