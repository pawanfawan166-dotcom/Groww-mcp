from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pyotp
from growwapi import GrowwAPI

from groww_mcp.config import Settings

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
        response = self._ensure_client().get_ltp(
            (exchange_symbol,),
            segment=GrowwAPI.SEGMENT_CASH,
            timeout=15,
        )
        ltp = response.get(exchange_symbol) if isinstance(response, dict) else response
        return {
            "mode": "live",
            "trading_symbol": trading_symbol.upper(),
            "exchange": exchange.upper(),
            "ltp": ltp,
        }
