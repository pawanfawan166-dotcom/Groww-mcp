#!/usr/bin/env python3
"""Verify Groww credentials are available to the scanner."""

from groww_mcp.config import Settings

if __name__ == "__main__":
    settings = Settings.from_env()
    if settings.has_credentials():
        print("Groww credentials: OK (live mode)")
    else:
        print("Groww credentials: MISSING")
        print("Set GROWW_ACCESS_TOKEN or GROWW_API_KEY + GROWW_TOTP_SECRET in environment secrets.")
