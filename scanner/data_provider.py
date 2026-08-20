"""Market data via Groww API (live) with Groww-managed fallbacks."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from growwapi import GrowwAPI

from groww_mcp.config import Settings
from groww_mcp.groww_client import GrowwClient
from scanner.groww_adapters import candles_to_dataframe, groww_symbol, normalize_option_chain

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


@dataclass
class MarketSnapshot:
    symbol: str
    daily: pd.DataFrame
    intraday: pd.DataFrame
    quote: dict[str, Any] = field(default_factory=dict)
    option_chain: dict[str, Any] = field(default_factory=dict)
    catalysts: list[str] = field(default_factory=list)
    sector: str = "Other"
    price_sources: list[str] = field(default_factory=list)


class GrowwDataProvider:
    """Fetch scanner inputs exclusively through GrowwClient."""

    def __init__(self) -> None:
        self._client = GrowwClient(Settings.from_env())
        self._nifty_daily: pd.DataFrame | None = None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Referer": "https://www.nseindia.com/",
            }
        )

    @property
    def has_live_credentials(self) -> bool:
        return Settings.from_env().has_credentials()

    def get_nifty_daily(self) -> pd.DataFrame:
        if self._nifty_daily is None:
            self._nifty_daily = self._fetch_candles("NIFTY", "FNO", GrowwAPI.CANDLE_INTERVAL_DAY, days=60)
        return self._nifty_daily

    def fetch_snapshot(self, symbol: str, sector: str) -> MarketSnapshot | None:
        time.sleep(0.12)
        sources: list[str] = []

        daily = self._fetch_candles(symbol, "CASH", GrowwAPI.CANDLE_INTERVAL_DAY, days=60)
        if daily.empty or len(daily) < 15:
            return None

        intraday = self._fetch_candles(symbol, "CASH", GrowwAPI.CANDLE_INTERVAL_MIN_5, days=5)
        quote_payload = self._safe_call(self._client.get_quote, symbol, "NSE", "CASH")
        quote = quote_payload.get("quote", {}) if quote_payload else {}
        if quote_payload:
            sources.append(str(quote_payload.get("price_source", "groww")))

        spot = float(quote.get("last_price") or daily["Close"].iloc[-1])
        option_chain = self._fetch_option_chain(symbol, spot, sources)
        catalysts = self._fetch_catalysts(symbol)

        return MarketSnapshot(
            symbol=symbol,
            daily=daily,
            intraday=intraday,
            quote={
                "sector": sector,
                "last_price": spot,
                "day_change_perc": quote.get("day_change_perc"),
                "volume": quote.get("volume"),
                "ohlc": quote.get("ohlc", {}),
            },
            option_chain=option_chain,
            catalysts=catalysts,
            sector=sector,
            price_sources=sorted(set(sources)),
        )

    def _fetch_candles(self, symbol: str, segment: str, interval: str, days: int) -> pd.DataFrame:
        end = datetime.now(IST)
        start = end - timedelta(days=days)
        payload = self._safe_call(
            self._client.get_historical_candles,
            "NSE",
            segment,
            groww_symbol("NSE", symbol),
            start.strftime("%Y-%m-%d %H:%M:%S"),
            end.strftime("%Y-%m-%d %H:%M:%S"),
            interval,
        )
        if not payload:
            return pd.DataFrame()
        frame = candles_to_dataframe(payload.get("data", payload))
        return frame

    def _fetch_option_chain(self, symbol: str, spot: float, sources: list[str]) -> dict[str, Any]:
        expiries_payload = self._safe_call(self._client.get_expiries, "NSE", symbol)
        expiries = []
        if expiries_payload:
            raw = expiries_payload.get("expiries", expiries_payload.get("data", {}))
            if isinstance(raw, dict):
                expiries = raw.get("expiries", [])
            elif isinstance(raw, list):
                expiries = raw
            sources.append(str(expiries_payload.get("price_source", "groww")))

        if not expiries:
            return {}

        expiry = expiries[0]
        chain_payload = self._safe_call(self._client.get_option_chain, symbol, expiry, "NSE")
        if not chain_payload:
            return {}
        sources.append(str(chain_payload.get("price_source", "groww")))
        return normalize_option_chain(chain_payload, spot)

    def _fetch_catalysts(self, symbol: str) -> list[str]:
        catalysts: list[str] = []
        try:
            self._session.get("https://www.nseindia.com/", timeout=10)
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
        except Exception as exc:
            logger.debug("Catalyst fetch failed for %s: %s", symbol, exc)
        return catalysts[:5]

    def batch_sector_returns(self, snapshots: dict[str, MarketSnapshot]) -> dict[str, float]:
        sector_moves: dict[str, list[float]] = {}
        for snap in snapshots.values():
            daily = snap.daily
            if len(daily) < 2:
                continue
            move = (daily["Close"].iloc[-1] / daily["Close"].iloc[-2] - 1) * 100
            sector_moves.setdefault(snap.sector, []).append(move)
        return {sector: sum(vals) / len(vals) for sector, vals in sector_moves.items() if vals}

    @staticmethod
    def _safe_call(func, *args, **kwargs) -> dict[str, Any] | None:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.debug("Groww call %s failed: %s", func.__name__, exc)
            return None


# Backwards-compatible alias used by scanner
MarketDataProvider = GrowwDataProvider
