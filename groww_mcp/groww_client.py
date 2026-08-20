from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pyotp
from growwapi import GrowwAPI

from groww_mcp.config import Settings
from groww_mcp.market_data import (
    fetch_contracts as fetch_contracts_fallback,
    fetch_expiries as fetch_expiries_fallback,
    fetch_greeks as fetch_greeks_fallback,
    fetch_historical_candles as fetch_historical_candles_fallback,
    fetch_ltp as fetch_ltp_fallback,
    fetch_ohlc as fetch_ohlc_fallback,
    fetch_option_chain_summary as fetch_option_chain_fallback,
    fetch_quote as fetch_quote_fallback,
)

IST = ZoneInfo("Asia/Kolkata")


class GrowwClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: GrowwAPI | None = None
        self._token_date: datetime | None = None

    def _is_expired(self) -> bool:
        if self._settings.access_token:
            return False
        if self._token_date is None:
            return True
        now = datetime.now(IST)
        today_expiry = now.replace(hour=6, minute=0, second=0, microsecond=0)
        return now >= today_expiry and self._token_date < today_expiry

    def _resolve_access_token(self) -> str:
        if self._settings.access_token:
            return self._settings.access_token

        api_key = self._settings.api_key
        if not api_key:
            raise ValueError(
                "Groww credentials missing. Set GROWW_ACCESS_TOKEN or "
                "GROWW_API_KEY with GROWW_TOTP_SECRET / GROWW_API_SECRET."
            )

        if self._settings.totp_secret:
            totp = pyotp.TOTP(self._settings.totp_secret).now()
            return GrowwAPI.get_access_token(api_key=api_key, totp=totp)

        if self._settings.api_secret:
            return GrowwAPI.get_access_token(api_key=api_key, secret=self._settings.api_secret)

        raise ValueError(
            "Groww API key found but no TOTP secret or API secret. "
            "Set GROWW_TOTP_SECRET or GROWW_API_SECRET."
        )

    def _ensure_client(self) -> GrowwAPI:
        if self._client is None or self._is_expired():
            token = self._resolve_access_token()
            self._client = GrowwAPI(token)
            self._token_date = datetime.now(IST)
        return self._client

    @staticmethod
    def _resolve_segment(segment: str) -> str:
        segment = segment.upper()
        if segment in {GrowwAPI.SEGMENT_CASH, GrowwAPI.SEGMENT_FNO, GrowwAPI.SEGMENT_COMMODITY}:
            return segment
        mapping = {
            "CASH": GrowwAPI.SEGMENT_CASH,
            "FNO": GrowwAPI.SEGMENT_FNO,
            "COMMODITY": GrowwAPI.SEGMENT_COMMODITY,
            "EQUITY": GrowwAPI.SEGMENT_CASH,
        }
        if segment not in mapping:
            raise ValueError(f"Unsupported segment: {segment}")
        return mapping[segment]

    @staticmethod
    def _exchange_symbol(exchange: str, trading_symbol: str) -> str:
        return f"{exchange.upper()}_{trading_symbol.upper()}"

    def get_holdings(self) -> dict[str, Any]:
        response = self._ensure_client().get_holdings_for_user(timeout=15)
        holdings = response.get("holdings", response) if isinstance(response, dict) else response
        return {"mode": "live", "holdings": holdings}

    def get_ltp(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> dict[str, Any]:
        symbols = [s.strip() for s in trading_symbol.split(",") if s.strip()]
        if len(symbols) == 1:
            return self._get_single_ltp(symbols[0], exchange, segment)

        rows: dict[str, Any] = {}
        sources: set[str] = set()
        for symbol in symbols[:50]:
            item = self._get_single_ltp(symbol, exchange, segment)
            key = self._exchange_symbol(exchange, symbol)
            rows[key] = item["ltp"]
            sources.add(str(item["price_source"]))

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "ltp": rows,
            "price_source": sorted(sources),
        }

    def _get_single_ltp(self, trading_symbol: str, exchange: str, segment: str) -> dict[str, Any]:
        exchange_symbol = self._exchange_symbol(exchange, trading_symbol)
        price_source = "groww"
        try:
            response = self._ensure_client().get_ltp(
                (exchange_symbol,),
                segment=self._resolve_segment(segment),
                timeout=15,
            )
            ltp = response.get(exchange_symbol) if isinstance(response, dict) else response
        except Exception:
            ltp = fetch_ltp_fallback(trading_symbol, exchange)
            price_source = "yahoo_finance"

        return {
            "mode": "live",
            "trading_symbol": trading_symbol.upper(),
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "ltp": ltp,
            "price_source": price_source,
        }

    def get_quote(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_quote(
                trading_symbol=trading_symbol.upper(),
                exchange=exchange.upper(),
                segment=self._resolve_segment(segment),
                timeout=15,
            )
        except Exception:
            data = fetch_quote_fallback(trading_symbol, exchange)
            price_source = "yahoo_finance"

        return {
            "mode": "live",
            "trading_symbol": trading_symbol.upper(),
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "quote": data,
            "price_source": price_source,
        }

    def get_ohlc(
        self,
        trading_symbol: str,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> dict[str, Any]:
        symbols = [s.strip() for s in trading_symbol.split(",") if s.strip()]
        exchange_symbols = tuple(self._exchange_symbol(exchange, s) for s in symbols[:50])
        price_source = "groww"
        try:
            data = self._ensure_client().get_ohlc(
                exchange_symbols,
                segment=self._resolve_segment(segment),
                timeout=15,
            )
        except Exception:
            data = {
                self._exchange_symbol(exchange, symbol): fetch_ohlc_fallback(symbol, exchange)
                for symbol in symbols
            }
            price_source = "yahoo_finance"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "ohlc": data,
            "price_source": price_source,
        }

    def get_option_chain(
        self,
        underlying: str,
        expiry_date: str,
        exchange: str = "NSE",
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_option_chain(
                exchange=exchange.upper(),
                underlying=underlying.upper(),
                expiry_date=expiry_date,
                timeout=15,
            )
        except Exception:
            data = fetch_option_chain_fallback(underlying, exchange, expiry_date)
            price_source = "yahoo_finance"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "underlying": underlying.upper(),
            "expiry_date": expiry_date,
            "option_chain": data,
            "price_source": price_source,
        }

    def get_greeks(
        self,
        exchange: str,
        underlying: str,
        trading_symbol: str,
        expiry: str,
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_greeks(
                exchange=exchange.upper(),
                underlying=underlying.upper(),
                trading_symbol=trading_symbol.upper(),
                expiry=expiry,
            )
        except Exception:
            data = fetch_greeks_fallback(underlying, trading_symbol, expiry, exchange)
            price_source = "black_scholes_estimate"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "underlying": underlying.upper(),
            "trading_symbol": trading_symbol.upper(),
            "expiry": expiry,
            "greeks": data,
            "price_source": price_source,
        }

    def get_historical_candles(
        self,
        exchange: str,
        segment: str,
        groww_symbol: str,
        start_time: str,
        end_time: str,
        candle_interval: str = "1day",
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_historical_candles(
                exchange=exchange.upper(),
                segment=self._resolve_segment(segment),
                groww_symbol=groww_symbol.upper(),
                start_time=start_time,
                end_time=end_time,
                candle_interval=candle_interval,
                timeout=15,
            )
        except Exception:
            data = fetch_historical_candles_fallback(
                groww_symbol, exchange, start_time, end_time, candle_interval
            )
            price_source = "yahoo_finance"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "segment": segment.upper(),
            "symbol": groww_symbol.upper(),
            "candle_interval": candle_interval,
            "data": data,
            "price_source": price_source,
        }

    def get_expiries(
        self,
        exchange: str,
        underlying_symbol: str,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_expiries(
                exchange=exchange.upper(),
                underlying_symbol=underlying_symbol.upper(),
                year=year,
                month=month,
                timeout=15,
            )
        except Exception:
            data = fetch_expiries_fallback(underlying_symbol, exchange, year, month)
            price_source = "calendar_estimate"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "underlying_symbol": underlying_symbol.upper(),
            "expiries": data,
            "price_source": price_source,
        }

    def get_contracts(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: str,
    ) -> dict[str, Any]:
        price_source = "groww"
        try:
            data = self._ensure_client().get_contracts(
                exchange=exchange.upper(),
                underlying_symbol=underlying_symbol.upper(),
                expiry_date=expiry_date,
                timeout=15,
            )
        except Exception:
            data = fetch_contracts_fallback(underlying_symbol, expiry_date, exchange)
            price_source = "synthetic_estimate"

        return {
            "mode": "live",
            "exchange": exchange.upper(),
            "underlying_symbol": underlying_symbol.upper(),
            "expiry_date": expiry_date,
            "contracts": data,
            "price_source": price_source,
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        holdings_data = self.get_holdings()["holdings"]
        rows: list[dict[str, Any]] = []
        total_invested = 0.0
        total_current = 0.0
        price_sources: set[str] = set()

        for holding in holdings_data:
            symbol = holding["trading_symbol"]
            qty = float(holding["quantity"])
            avg = float(holding["average_price"])
            invested = qty * avg
            ltp_info = self.get_ltp(symbol)
            ltp = float(ltp_info["ltp"])
            current = qty * ltp
            pnl = current - invested
            price_sources.add(str(ltp_info.get("price_source", "groww")))

            rows.append(
                {
                    "trading_symbol": symbol,
                    "quantity": qty,
                    "average_price": avg,
                    "ltp": ltp,
                    "invested": round(invested, 2),
                    "current_value": round(current, 2),
                    "pnl": round(pnl, 2),
                    "pnl_percent": round((pnl / invested) * 100, 2) if invested else 0.0,
                    "price_source": ltp_info.get("price_source", "groww"),
                    "isin": holding.get("isin"),
                }
            )
            total_invested += invested
            total_current += current

        total_pnl = total_current - total_invested
        return {
            "mode": "live",
            "price_source": sorted(price_sources),
            "holdings": rows,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / total_invested) * 100, 2) if total_invested else 0.0,
        }
