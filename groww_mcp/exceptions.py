"""Groww API errors with actionable fix hints."""

from __future__ import annotations


class GrowwAPIError(Exception):
    """Base Groww client error."""


class GrowwMarketDataForbiddenError(GrowwAPIError):
    """Market data blocked — subscription, IP whitelist, or daily approval required."""

    FIX_STEPS = (
        "1. Subscribe to Groww Trading API (₹499/month + tax): https://groww.in/trade-api",
        "2. Groww Cloud → API Keys → Add Static IP: whitelist this agent's public IP",
        "3. TOTP/API key → daily approval on Groww Cloud if prompted",
        "4. Regenerate access token after IP/subscription changes",
    )

    def __init__(self, message: str, endpoint: str = "") -> None:
        self.endpoint = endpoint
        detail = f"{message}\n\nGroww market data fix:\n" + "\n".join(self.FIX_STEPS)
        if endpoint:
            detail = f"[{endpoint}] {detail}"
        super().__init__(detail)
