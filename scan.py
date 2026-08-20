#!/usr/bin/env python3
"""CLI for early extreme-momentum scanner (Groww data)."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from groww_mcp.config import Settings
from scanner.early_momentum_scanner import EarlyMomentumScanner
from scanner.output import format_leaderboard, format_top_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="NSE F&O Early Extreme-Momentum Scanner (Groww)")
    parser.add_argument("--limit", type=int, default=None, help="Limit universe size for testing")
    parser.add_argument("--top", type=int, default=10, help="Show top N candidates")
    parser.add_argument("--symbol", type=str, default=None, help="Scan single symbol")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    creds = Settings.from_env()
    if creds.has_credentials():
        print("Data source: Groww API (strict — no Yahoo fallback)")
        import subprocess
        result = subprocess.run(
            ["python3", "scripts/groww_diagnose.py"],
            cwd=os.path.dirname(os.path.dirname(__file__)) or ".",
            capture_output=True,
            text=True,
        )
        if result.returncode == 2:
            print(result.stdout)
            print("Scanner cannot run until Groww market data is enabled.")
            return 2
        if result.returncode != 0:
            print(result.stdout or result.stderr)
    else:
        print("Data source: credentials missing — set GROWW_API_KEY + GROWW_TOTP_SECRET")
    print()

    scanner = EarlyMomentumScanner()
    symbols = [args.symbol.upper()] if args.symbol else None
    candidates = scanner.scan(symbols=symbols, limit=args.limit)
    top = scanner.top_candidate(candidates)

    print(format_top_candidate(top))
    print()
    print(format_leaderboard(candidates, n=args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
