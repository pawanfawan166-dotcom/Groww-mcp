from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pyotp
from growwapi import GrowwAPI

from groww_mcp.config import Settings
from groww_mcp.market_data import fetch_ltp as fetch_ltp_fallback

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

    def get_holdings(self) -> dict[str, Any]:
        response = self._ensure_client().get_holdings_for_user(timeout=15)
        holdings = response.get("holdings", response) if isinstance(response, dict) else response
        return {"mode": "live", "holdings": holdings}

    def get_ltp(self, trading_symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        exchange_symbol = f"{exchange.upper()}_{trading_symbol.upper()}"
        price_source = "groww"
        try:
            response = self._ensure_client().get_ltp(
                (exchange_symbol,),
                segment=GrowwAPI.SEGMENT_CASH,
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
            "ltp": ltp,
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
