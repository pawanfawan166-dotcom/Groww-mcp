"""Market data provider with yfinance fallback and optional NSE enrichment."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from scanner.universe import yfinance_symbol

_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 1.5


def _fetch_history(ticker: yf.Ticker, **kwargs: Any) -> pd.DataFrame:
    for attempt in range(_MAX_RETRIES):
        try:
            frame = ticker.history(**kwargs)
            if not frame.empty:
                return frame
        except Exception:
            if attempt == _MAX_RETRIES - 1:
                raise
        time.sleep(_RETRY_DELAY_SEC * (attempt + 1))
    return pd.DataFrame()


@dataclass
class MarketSnapshot:
    symbol: str
    daily: pd.DataFrame
    intraday: pd.DataFrame
    quote: dict[str, Any] = field(default_factory=dict)
    option_chain: dict[str, Any] = field(default_factory=dict)
    catalysts: list[str] = field(default_factory=list)
    sector: str = "Other"


class MarketDataProvider:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Referer": "https://www.nseindia.com/",
            }
        )
        self._session_initialized = False
        self._nifty_daily: pd.DataFrame | None = None
        self._sector_returns: dict[str, float] = {}

    def _ensure_nse_session(self) -> None:
        if not self._session_initialized:
            self._session.get("https://www.nseindia.com/", timeout=15)
            self._session_initialized = True

    def get_nifty_daily(self) -> pd.DataFrame:
        if self._nifty_daily is None:
            self._nifty_daily = _fetch_history(yf.Ticker("^NSEI"), period="60d", interval="1d")
        return self._nifty_daily

    def fetch_snapshot(self, symbol: str, sector: str) -> MarketSnapshot | None:
        time.sleep(0.15)
        ticker = yf.Ticker(yfinance_symbol(symbol))
        daily = _fetch_history(ticker, period="60d", interval="1d")
        if daily.empty or len(daily) < 15:
            return None

        intraday = _fetch_history(ticker, period="5d", interval="5m")
        catalysts = self._fetch_catalysts(symbol, ticker)
        option_chain = self._fetch_option_chain(symbol)

        quote = {
            "sector": sector,
            "market_cap": ticker.info.get("marketCap"),
            "avg_volume": ticker.info.get("averageVolume"),
        }
        return MarketSnapshot(
            symbol=symbol,
            daily=daily,
            intraday=intraday,
            quote=quote,
            option_chain=option_chain,
            catalysts=catalysts,
            sector=sector,
        )

    def _fetch_catalysts(self, symbol: str, ticker: yf.Ticker) -> list[str]:
        catalysts: list[str] = []
        try:
            news = ticker.news or []
            for item in news[:5]:
                title = item.get("title") or item.get("content", {}).get("title")
                if title:
                    catalysts.append(title)
        except Exception:
            pass

        try:
            self._ensure_nse_session()
            response = self._session.get(
                "https://www.nseindia.com/api/live-analysis-variations?index=gainers",
                timeout=10,
            )
            if response.ok:
                payload = response.json()
                for bucket in payload.values():
                    if not isinstance(bucket, dict):
                        continue
                    for row in bucket.get("data", []):
                        if row.get("symbol") == symbol and row.get("ca_purpose"):
                            catalysts.append(row["ca_purpose"])
        except Exception:
            pass

        deduped: list[str] = []
        seen: set[str] = set()
        for item in catalysts:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped[:5]

    def _fetch_option_chain(self, symbol: str) -> dict[str, Any]:
        try:
            self._ensure_nse_session()
            response = self._session.get(
                f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}",
                timeout=10,
            )
            if response.ok and response.content:
                return response.json()
        except Exception:
            pass
        return {}

    def batch_sector_returns(self, snapshots: dict[str, MarketSnapshot]) -> dict[str, float]:
        sector_moves: dict[str, list[float]] = {}
        for snap in snapshots.values():
            daily = snap.daily
            if len(daily) < 2:
                continue
            move = (daily["Close"].iloc[-1] / daily["Close"].iloc[-2] - 1) * 100
            sector_moves.setdefault(snap.sector, []).append(move)
        return {sector: sum(vals) / len(vals) for sector, vals in sector_moves.items() if vals}
