"""
stock_tools.py – CrewAI tools for fundamental and technical stock analysis.

Tools
─────
  StockDataTool          →  yfinance fundamental data
  TechnicalAnalysisTool  →  technical indicators via the `ta` package

Rate-limit strategy (yfinance ≥1.0.0)
───────────────────────────────────────
  • yfinance ≥1.0.0 has a completely rewritten HTTP layer with automatic
    cookie/crumb management and built-in 429 recovery — this is the primary
    fix for "Too Many Requests" errors seen with 0.2.x.
  • For fundamental data : try `ticker.fast_info` (lightweight endpoint) first,
    then fall back to `ticker.info` (full quoteSummary) for deeper fields.
  • For OHLCV / technical data : use `yf.download()` which hits a different,
    far-less-rate-limited endpoint compared with `ticker.history()`.
  • Random jitter sleep (1–3 s) before each outbound call prevents
    back-to-back burst requests from the same process.
  • Module-level TTL cache (5 min) avoids duplicate fetches within one
    analysis session (two agents asking for the same ticker share the result).
"""

from __future__ import annotations

import json
import random
import time
import warnings
from threading import Lock
from typing import Any, Type

import pandas as pd
import yfinance as yf
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ── Suppress deprecation noise from yfinance / pandas internals ───────────────
for _pat in (".*Timestamp.utcnow.*", ".*utcnow.*"):
    warnings.filterwarnings("ignore", message=_pat, category=FutureWarning)
    warnings.filterwarnings("ignore", message=_pat, category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning,     module="yfinance")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="yfinance")

try:
    import ta
    _TA_AVAILABLE = True
except ImportError:
    _TA_AVAILABLE = False


# ── TTL cache ─────────────────────────────────────────────────────────────────

_CACHE_LOCK  = Lock()
_INFO_CACHE: dict[str, dict]        = {}
_HIST_CACHE: dict[str, pd.DataFrame] = {}
_CACHE_TS:   dict[str, float]       = {}
_CACHE_TTL   = 300   # 5-minute TTL


def _jitter_sleep(lo: float = 1.0, hi: float = 3.0) -> None:
    """Random sleep to avoid request bursts."""
    time.sleep(random.uniform(lo, hi))


def _get_info(symbol: str) -> dict:
    """
    Fetch Ticker.info with caching.
    Falls back to fast_info for lightweight price fields when info is empty.
    yfinance ≥1.0.0 handles cookies/crumbs and 429-retry internally.
    """
    key = f"info:{symbol.upper()}"
    with _CACHE_LOCK:
        if key in _INFO_CACHE and (time.time() - _CACHE_TS.get(key, 0)) < _CACHE_TTL:
            return _INFO_CACHE[key]

    _jitter_sleep(1.0, 2.5)
    ticker = yf.Ticker(symbol.upper())

    info: dict = {}
    try:
        info = ticker.info or {}
    except Exception:
        pass

    # Enrich from fast_info when core price fields are absent
    if not info.get("currentPrice") and not info.get("regularMarketPrice"):
        try:
            fi = ticker.fast_info
            info.update({
                "currentPrice":         getattr(fi, "last_price",              None),
                "regularMarketPrice":   getattr(fi, "last_price",              None),
                "previousClose":        getattr(fi, "previous_close",          None),
                "marketCap":            getattr(fi, "market_cap",              None),
                "fiftyTwoWeekHigh":     getattr(fi, "year_high",               None),
                "fiftyTwoWeekLow":      getattr(fi, "year_low",                None),
                "fiftyDayAverage":      getattr(fi, "fifty_day_average",       None),
                "twoHundredDayAverage": getattr(fi, "two_hundred_day_average", None),
                "currency":             getattr(fi, "currency",                "USD"),
                "exchange":             getattr(fi, "exchange",                "N/A"),
                "quoteType":            getattr(fi, "quote_type",              "N/A"),
                "sharesOutstanding":    getattr(fi, "shares",                  None),
            })
        except Exception:
            pass

    with _CACHE_LOCK:
        _INFO_CACHE[key] = info
        _CACHE_TS[key] = time.time()
    return info


def _get_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV via yf.download() (different, less-rate-limited endpoint).
    Falls back to ticker.history() if download returns empty.
    """
    key = f"hist:{symbol.upper()}:{period}"
    with _CACHE_LOCK:
        if key in _HIST_CACHE and (time.time() - _CACHE_TS.get(key, 0)) < _CACHE_TTL:
            return _HIST_CACHE[key]

    _jitter_sleep(1.5, 3.0)
    sym = symbol.upper()

    # Primary: yf.download
    df: pd.DataFrame = pd.DataFrame()
    try:
        df = yf.download(sym, period=period, auto_adjust=True, progress=False, timeout=30)
        # Flatten MultiIndex columns produced when downloading a single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
    except Exception:
        df = pd.DataFrame()

    # Fallback: ticker.history
    if df.empty:
        _jitter_sleep(2.0, 4.0)
        try:
            df = yf.Ticker(sym).history(period=period)
        except Exception:
            df = pd.DataFrame()

    with _CACHE_LOCK:
        _HIST_CACHE[key] = df
        _CACHE_TS[key] = time.time()
    return df


# ── Input schema ──────────────────────────────────────────────────────────────

class StockInput(BaseModel):
    symbol: str = Field(
        ...,
        description=(
            "Stock ticker symbol. US stocks: AAPL, TSLA, NVDA. "
            "Indian NSE stocks: TCS.NS, RELIANCE.NS. "
            "Indian BSE stocks: TCS.BO. "
            "Do NOT append .NS or .BO to US tickers."
        ),
    )


# ── Format helper ─────────────────────────────────────────────────────────────

def _fmt(val: Any, pct: bool = False, bil: bool = True) -> str:
    """Format a numeric value for display."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if pct:
            return f"{v * 100:.2f}%"
        if bil and abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if bil and abs(v) >= 1e6:
            return f"${v / 1e6:.2f}M"
        return f"{v:.4f}" if abs(v) < 10 else f"{v:.2f}"
    except Exception:
        return str(val)


# ── StockDataTool ─────────────────────────────────────────────────────────────

class StockDataTool(BaseTool):
    name: str = "Get Stock Fundamental Data"
    description: str = (
        "Fetches comprehensive fundamental data for a stock symbol including "
        "company information, valuation ratios (P/E, PEG, P/B, EV/EBITDA), "
        "profitability metrics, balance sheet health, analyst consensus, and dividend info."
    )
    args_schema: Type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        sym = symbol.strip().upper()
        try:
            info = _get_info(sym)

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not current_price:
                return (
                    f"⚠️  No price data found for '{sym}'. "
                    "Verify the ticker is correct (for US stocks omit .NS/.BO). "
                    "Yahoo Finance may also be temporarily rate-limiting; retry in ~60 s."
                )

            data = {
                # Identity
                "symbol":           sym,
                "company_name":     info.get("longName") or info.get("shortName", "N/A"),
                "exchange":         info.get("exchange", "N/A"),
                "sector":           info.get("sector", "N/A"),
                "industry":         info.get("industry", "N/A"),
                "country":          info.get("country", "N/A"),
                "currency":         info.get("currency", "USD"),
                # Price
                "current_price":         _fmt(current_price, bil=False),
                "previous_close":        _fmt(info.get("previousClose"), bil=False),
                "open_price":            _fmt(info.get("open"), bil=False),
                "day_high":              _fmt(info.get("dayHigh"), bil=False),
                "day_low":               _fmt(info.get("dayLow"), bil=False),
                "52w_high":              _fmt(info.get("fiftyTwoWeekHigh"), bil=False),
                "52w_low":               _fmt(info.get("fiftyTwoWeekLow"), bil=False),
                "50d_avg":               _fmt(info.get("fiftyDayAverage"), bil=False),
                "200d_avg":              _fmt(info.get("twoHundredDayAverage"), bil=False),
                # Size
                "market_cap":            _fmt(info.get("marketCap")),
                "enterprise_value":      _fmt(info.get("enterpriseValue")),
                "shares_outstanding":    _fmt(info.get("sharesOutstanding")),
                # Valuation
                "pe_ratio_ttm":          _fmt(info.get("trailingPE"), bil=False),
                "pe_ratio_forward":      _fmt(info.get("forwardPE"), bil=False),
                "peg_ratio":             _fmt(info.get("pegRatio"), bil=False),
                "price_to_book":         _fmt(info.get("priceToBook"), bil=False),
                "price_to_sales_ttm":    _fmt(info.get("priceToSalesTrailingTwelveMonths"), bil=False),
                "ev_to_ebitda":          _fmt(info.get("enterpriseToEbitda"), bil=False),
                # Earnings
                "eps_ttm":               _fmt(info.get("trailingEps"), bil=False),
                "eps_forward":           _fmt(info.get("forwardEps"), bil=False),
                # Revenue & profitability
                "revenue_ttm":           _fmt(info.get("totalRevenue")),
                "revenue_growth_yoy":    _fmt(info.get("revenueGrowth"), pct=True, bil=False),
                "earnings_growth_yoy":   _fmt(info.get("earningsGrowth"), pct=True, bil=False),
                "gross_margin":          _fmt(info.get("grossMargins"), pct=True, bil=False),
                "operating_margin":      _fmt(info.get("operatingMargins"), pct=True, bil=False),
                "net_profit_margin":     _fmt(info.get("profitMargins"), pct=True, bil=False),
                "ebitda":                _fmt(info.get("ebitda")),
                # Returns
                "roe":                   _fmt(info.get("returnOnEquity"), pct=True, bil=False),
                "roa":                   _fmt(info.get("returnOnAssets"), pct=True, bil=False),
                # Balance sheet
                "total_cash":            _fmt(info.get("totalCash")),
                "total_debt":            _fmt(info.get("totalDebt")),
                "debt_to_equity":        _fmt(info.get("debtToEquity"), bil=False),
                "current_ratio":         _fmt(info.get("currentRatio"), bil=False),
                "quick_ratio":           _fmt(info.get("quickRatio"), bil=False),
                "free_cash_flow":        _fmt(info.get("freeCashflow")),
                # Dividends
                "dividend_yield":        _fmt(info.get("dividendYield"), pct=True, bil=False),
                "dividend_rate":         _fmt(info.get("dividendRate"), bil=False),
                "payout_ratio":          _fmt(info.get("payoutRatio"), pct=True, bil=False),
                # Analyst consensus
                "analyst_target_price":  _fmt(info.get("targetMeanPrice"), bil=False),
                "analyst_low_target":    _fmt(info.get("targetLowPrice"), bil=False),
                "analyst_high_target":   _fmt(info.get("targetHighPrice"), bil=False),
                "analyst_recommendation": info.get("recommendationKey", "N/A"),
                "number_of_analysts":    info.get("numberOfAnalystOpinions", "N/A"),
                # Risk / misc
                "beta":                  _fmt(info.get("beta"), bil=False),
                "short_ratio":           _fmt(info.get("shortRatio"), bil=False),
                # Description
                "business_summary": (
                    (info.get("longBusinessSummary") or "N/A")[:700]
                ),
            }

            return json.dumps(data, indent=2, default=str)

        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too Many Requests" in msg:
                return (
                    f"⚠️  Yahoo Finance is rate-limiting requests for '{sym}'. "
                    "Please wait 60–120 seconds and retry. "
                    "If this persists, try a different network or VPN."
                )
            return f"Error fetching fundamental data for '{sym}': {msg}"


# ── TechnicalAnalysisTool ─────────────────────────────────────────────────────

class TechnicalAnalysisTool(BaseTool):
    name: str = "Get Technical Analysis Indicators"
    description: str = (
        "Performs comprehensive technical analysis on a stock using 1 year of daily OHLCV data. "
        "Returns RSI, MACD, Bollinger Bands, SMA/EMA (20/50/200), Stochastic, ATR, "
        "volume analysis, period returns, and an overall trend assessment."
    )
    args_schema: Type[BaseModel] = StockInput

    def _run(self, symbol: str) -> str:
        sym = symbol.strip().upper()
        try:
            # yf.download() is used internally (less rate-limited endpoint)
            df = _get_history(sym, period="1y")

            if df is None or df.empty or len(df) < 30:
                return (
                    f"⚠️  Insufficient historical data for '{sym}'. "
                    "Verify the ticker symbol and try again. "
                    "(Yahoo Finance may also be temporarily rate-limiting; retry in ~60 s.)"
                )

            # Normalise column names across yfinance versions
            df.columns = [str(c).strip().title() for c in df.columns]

            def _col(name: str) -> pd.Series:
                aliases = {
                    "Close":  ["Close", "Adj Close", "Adj_Close"],
                    "High":   ["High"],
                    "Low":    ["Low"],
                    "Volume": ["Volume"],
                }
                for alias in aliases.get(name, [name]):
                    if alias in df.columns:
                        return df[alias].squeeze()
                raise KeyError(f"Column '{name}' not found in {list(df.columns)}")

            close  = _col("Close").dropna()
            high   = _col("High").reindex(close.index).ffill()
            low    = _col("Low").reindex(close.index).ffill()
            volume = _col("Volume").reindex(close.index).ffill()

            current = float(close.iloc[-1])
            prev    = float(close.iloc[-2])
            res: dict = {}

            # ── Price action ───────────────────────────────────────────────
            res["current_price"]     = round(current, 4)
            res["prev_close"]        = round(prev, 4)
            res["daily_change"]      = round(current - prev, 4)
            res["daily_change_pct"]  = round((current - prev) / prev * 100, 2)
            res["52w_high"]          = round(float(close.max()), 4)
            res["52w_low"]           = round(float(close.min()), 4)
            res["pct_from_52w_high"] = round((current - float(close.max())) / float(close.max()) * 100, 2)
            res["pct_from_52w_low"]  = round((current - float(close.min())) / float(close.min()) * 100, 2)

            # ── Period returns ─────────────────────────────────────────────
            def _ret(n: int) -> str:
                if len(close) >= n:
                    base = float(close.iloc[-n])
                    return f"{(current - base) / base * 100:.2f}%" if base else "N/A"
                return "N/A"

            res["1w_return"]  = _ret(5)
            res["1m_return"]  = _ret(21)
            res["3m_return"]  = _ret(63)
            res["6m_return"]  = _ret(126)
            res["ytd_return"] = (
                f"{(current - float(close.iloc[0])) / float(close.iloc[0]) * 100:.2f}%"
            )

            # ── Technical indicators ───────────────────────────────────────
            if _TA_AVAILABLE:
                def _v(s: pd.Series) -> float | str:
                    val = s.iloc[-1]
                    return round(float(val), 4) if not pd.isna(val) else "N/A"

                # RSI
                rsi_val = _v(ta.momentum.RSIIndicator(close, window=14).rsi())
                res["rsi_14"]     = rsi_val
                res["rsi_signal"] = (
                    "Overbought (>70)" if isinstance(rsi_val, float) and rsi_val > 70
                    else "Oversold (<30)" if isinstance(rsi_val, float) and rsi_val < 30
                    else "Neutral (30–70)"
                )

                # MACD
                _macd = ta.trend.MACD(close)
                mv = _v(_macd.macd())
                ms = _v(_macd.macd_signal())
                mh = _v(_macd.macd_diff())
                res.update({"macd": mv, "macd_signal_line": ms, "macd_histogram": mh})
                res["macd_crossover"] = (
                    "Bullish" if isinstance(mv, float) and isinstance(ms, float) and mv > ms
                    else "Bearish"
                )

                # Moving Averages
                sma20  = _v(ta.trend.SMAIndicator(close, window=20).sma_indicator())
                sma50  = _v(ta.trend.SMAIndicator(close, window=50).sma_indicator())
                sma200 = (
                    _v(ta.trend.SMAIndicator(close, window=200).sma_indicator())
                    if len(close) >= 200 else "N/A"
                )
                ema12  = _v(ta.trend.EMAIndicator(close, window=12).ema_indicator())
                ema26  = _v(ta.trend.EMAIndicator(close, window=26).ema_indicator())
                res.update({
                    "sma_20": sma20, "sma_50": sma50, "sma_200": sma200,
                    "ema_12": ema12, "ema_26": ema26,
                })
                res["above_sma_20"]  = isinstance(sma20,  float) and current > sma20
                res["above_sma_50"]  = isinstance(sma50,  float) and current > sma50
                res["above_sma_200"] = isinstance(sma200, float) and current > sma200
                res["golden_cross"]  = isinstance(sma50, float) and isinstance(sma200, float) and sma50 > sma200
                res["death_cross"]   = isinstance(sma50, float) and isinstance(sma200, float) and sma50 < sma200

                # Bollinger Bands
                _bb  = ta.volatility.BollingerBands(close, window=20)
                bb_u = _v(_bb.bollinger_hband())
                bb_m = _v(_bb.bollinger_mavg())
                bb_l = _v(_bb.bollinger_lband())
                res.update({"bb_upper": bb_u, "bb_middle": bb_m, "bb_lower": bb_l})
                res["bb_position"] = (
                    "Above Upper Band" if isinstance(bb_u, float) and current > bb_u
                    else "Below Lower Band" if isinstance(bb_l, float) and current < bb_l
                    else "Within Bands"
                )

                # ATR & Stochastic
                res["atr_14"] = _v(
                    ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
                )
                _st = ta.momentum.StochasticOscillator(high, low, close)
                res["stoch_k"] = _v(_st.stoch())
                res["stoch_d"] = _v(_st.stoch_signal())

                # Volume
                vol_avg = float(volume.rolling(20).mean().iloc[-1])
                cur_vol = int(volume.iloc[-1])
                res["current_volume"] = cur_vol
                res["volume_sma_20"]  = int(vol_avg)
                res["volume_ratio"]   = round(cur_vol / vol_avg, 2) if vol_avg else "N/A"
                res["volume_signal"]  = "Above Average" if cur_vol > vol_avg else "Below Average"

                # Overall trend score
                bull_pts = sum([
                    res["above_sma_50"],
                    res["above_sma_200"],
                    res["macd_crossover"] == "Bullish",
                    res["rsi_signal"] == "Neutral (30–70)",
                    res["golden_cross"],
                ])
                res["trend_assessment"] = (
                    "Strong Bullish" if bull_pts >= 4
                    else "Bullish"        if bull_pts == 3
                    else "Neutral"        if bull_pts == 2
                    else "Bearish"        if bull_pts == 1
                    else "Strong Bearish"
                )

            else:
                sma20 = round(float(close.tail(20).mean()), 4)
                sma50 = round(float(close.tail(50).mean()), 4)
                res.update({"sma_20": sma20, "sma_50": sma50})
                res["trend_assessment"] = "Bullish" if current > sma50 else "Bearish"

            return json.dumps({"symbol": sym, "technical_analysis": res}, indent=2, default=str)

        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "Too Many Requests" in msg:
                return (
                    f"⚠️  Yahoo Finance is rate-limiting requests for '{sym}'. "
                    "Please wait 60–120 seconds and retry. "
                    "If this persists, try a different network or VPN."
                )
            return f"Error performing technical analysis for '{sym}': {msg}"
