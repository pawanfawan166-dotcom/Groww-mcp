"""Relative strength vs Nifty and sector."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RelativeStrengthSignals:
    score: float
    details: list[str]
    vs_nifty: float
    vs_sector: float
    label: str


def analyze_relative_strength(
    daily: pd.DataFrame,
    nifty_daily: pd.DataFrame,
    sector_return: float | None,
    direction: str,
) -> RelativeStrengthSignals:
    details: list[str] = []
    score = 0.0

    stock_ret = (daily["Close"].iloc[-1] / daily["Close"].iloc[-2] - 1) * 100
    nifty_ret = (nifty_daily["Close"].iloc[-1] / nifty_daily["Close"].iloc[-2] - 1) * 100
    vs_nifty = stock_ret - nifty_ret

    # 5-day RS for trend
    stock_5d = (daily["Close"].iloc[-1] / daily["Close"].iloc[-6] - 1) * 100 if len(daily) >= 6 else stock_ret
    nifty_5d = (nifty_daily["Close"].iloc[-1] / nifty_daily["Close"].iloc[-6] - 1) * 100 if len(nifty_daily) >= 6 else nifty_ret
    rs_5d = stock_5d - nifty_5d

    vs_sector = stock_ret - (sector_return or 0.0)

    if direction == "bullish":
        if vs_nifty > 0.5:
            score += 4
            details.append(f"Outperforming Nifty by {vs_nifty:.2f}%")
        if rs_5d > 1.0:
            score += 3
            details.append("5-day relative strength building")
        if vs_sector > 0.3:
            score += 3
            details.append(f"Leading sector by {vs_sector:.2f}%")
        label = "Strong market + stronger stock" if nifty_ret >= 0 else "Weak market + resilient stock"
    else:
        if vs_nifty < -0.5:
            score += 4
            details.append(f"Underperforming Nifty by {vs_nifty:.2f}%")
        if rs_5d < -1.0:
            score += 3
            details.append("5-day relative weakness building")
        if vs_sector < -0.3:
            score += 3
            details.append(f"Lagging sector by {vs_sector:.2f}%")
        label = "Weak market + weaker stock" if nifty_ret <= 0 else "Strong market + unusually weak stock"

    score = min(score, 10.0)
    return RelativeStrengthSignals(
        score=score,
        details=details,
        vs_nifty=vs_nifty,
        vs_sector=vs_sector,
        label=label,
    )
