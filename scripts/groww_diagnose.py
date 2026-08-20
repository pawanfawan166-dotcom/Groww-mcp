#!/usr/bin/env python3
"""Diagnose Groww API access — shows exactly what works and what to fix."""

from __future__ import annotations

import json
import os
import urllib.request

import pyotp
from growwapi import GrowwAPI

from groww_mcp.config import Settings, allow_yahoo_fallback
from groww_mcp.exceptions import GrowwMarketDataForbiddenError
from groww_mcp.groww_client import GrowwClient


def _public_ip() -> str:
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=10).read().decode().strip()
    except Exception:
        return "unknown"


def main() -> int:
    ip = _public_ip()
    settings = Settings.from_env()
    strict = not allow_yahoo_fallback()

    print("=" * 60)
    print("GROWW API DIAGNOSTIC")
    print("=" * 60)
    print(f"Agent public IP (whitelist on Groww): {ip}")
    print(f"Groww-only mode: {'ON' if strict else 'OFF (Yahoo fallback allowed)'}")
    print()

    if not settings.has_credentials():
        print("❌ CREDENTIALS MISSING")
        print("Set GROWW_API_KEY + GROWW_TOTP_SECRET in environment secrets.")
        return 1

    print("✅ Credentials found")

    try:
        token = GrowwAPI.get_access_token(
            api_key=settings.api_key,
            totp=pyotp.TOTP(settings.totp_secret).now() if settings.totp_secret else None,
            secret=settings.api_secret,
        )
        print("✅ Access token generated")
    except Exception as exc:
        print(f"❌ Token generation failed: {exc}")
        return 1

    g = GrowwAPI(token)
    client = GrowwClient(settings)

    checks: list[tuple[str, str, bool, str]] = []

    def run(name: str, category: str, fn) -> None:
        try:
            fn()
            checks.append((name, category, True, "OK"))
        except Exception as exc:
            checks.append((name, category, False, str(exc).split("\n")[0][:120]))

    run("User profile", "account", lambda: g.get_user_profile(timeout=15))
    run("Holdings", "portfolio", lambda: client.get_holdings())
    run("Quote (RELIANCE)", "market_data", lambda: client.get_quote("RELIANCE"))
    run("LTP (RELIANCE)", "market_data", lambda: client.get_ltp("RELIANCE"))
    run("Historical candles", "market_data", lambda: client.get_historical_candles(
        "NSE", "CASH", "NSE_RELIANCE", "2026-07-01 09:15:00", "2026-08-20 15:30:00", "1day"
    ))
    run("Expiries (RELIANCE)", "fno", lambda: client.get_expiries("NSE", "RELIANCE"))
    run("Option chain", "fno", lambda: client.get_option_chain("RELIANCE", "2026-08-28"))

    print()
    print(f"{'Check':<22} {'Category':<14} {'Status'}")
    print("-" * 60)
    for name, category, ok, msg in checks:
        status = "✅ OK" if ok else f"❌ {msg}"
        print(f"{name:<22} {category:<14} {status}")

    portfolio_ok = any(c[2] for c in checks if c[1] == "portfolio")
    market_ok = all(c[2] for c in checks if c[1] in {"market_data", "fno"})

    print()
    if market_ok:
        print("✅ ALL GROWW TOOLS READY — scanner can run with live OI + options.")
        return 0

    if portfolio_ok and not market_ok:
        print("⚠️  PARTIAL ACCESS (common pattern)")
        print()
        print("Login works. Holdings work. Market data BLOCKED.")
        print()
        print("This is NOT a code bug. Groww server is rejecting market data.")
        print()
        print("FIX (all required for scanner):")
        print("  1. Subscribe: https://groww.in/trade-api  (₹499/month + tax)")
        print("     → Live Data API: Quote, LTP, OHLC, Historical, Option chain")
        print(f"  2. Whitelist IP: https://groww.in/trade-api/api-keys")
        print(f"     → Add Static IP: {ip}")
        print("  3. Groww Cloud → approve your API key for today (if prompted)")
        print("  4. Re-run: python scripts/groww_diagnose.py")
        print()
        print("Without subscription, Groww allows ONLY:")
        print("  • Profile, holdings, orders, positions, margin")
        print("NOT allowed without subscription:")
        print("  • Quotes, LTP, candles, OI, option chain")
        return 2

    print("❌ Groww access failed — check credentials.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
