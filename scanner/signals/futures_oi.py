"""Futures OI signal detection (live NSE when available, proxy otherwise)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class FuturesOISignals:
    score: float
    details: list[str]
    interpretation: str
    oi_building_early: bool


def analyze_futures_oi(
    daily: pd.DataFrame,
    option_chain: dict,
    direction: str,
    volume_relative: float,
) -> FuturesOISignals:
    details: list[str] = []
    score = 0.0
    interpretation = "Insufficient OI data"
    oi_building_early = False

    records = option_chain.get("records", {}) if option_chain else {}
    data = records.get("data", [])

    total_ce_oi_chg = 0.0
    total_pe_oi_chg = 0.0
    total_ce_vol = 0.0
    total_pe_vol = 0.0

    for row in data:
        ce = row.get("CE") or {}
        pe = row.get("PE") or {}
        total_ce_oi_chg += float(ce.get("changeinOpenInterest") or 0)
        total_pe_oi_chg += float(pe.get("changeinOpenInterest") or 0)
        total_ce_vol += float(ce.get("totalTradedVolume") or 0)
        total_pe_vol += float(pe.get("totalTradedVolume") or 0)

    has_oi = bool(data)
    today = daily.iloc[-1]
    prev = daily.iloc[-2]
    price_up = today["Close"] > prev["Close"]

    if has_oi:
        if price_up and total_ce_oi_chg > 0 and total_ce_oi_chg > abs(total_pe_oi_chg):
            interpretation = "Long buildup (Price ↑ + CE OI ↑)"
            score += 8
            details.append(interpretation)
        elif not price_up and total_pe_oi_chg > 0 and total_pe_oi_chg > abs(total_ce_oi_chg):
            interpretation = "Short buildup (Price ↓ + PE OI ↑)"
            score += 8
            details.append(interpretation)
        elif price_up and total_ce_oi_chg < 0:
            interpretation = "Short covering (Price ↑ + OI ↓)"
            score += 5
            details.append(interpretation)
        elif not price_up and total_pe_oi_chg < 0:
            interpretation = "Long unwinding (Price ↓ + OI ↓)"
            score += 4
            details.append(interpretation)

        # Early OI building: moderate OI change with volume expansion
        oi_magnitude = abs(total_ce_oi_chg) + abs(total_pe_oi_chg)
        if 0 < oi_magnitude < 500000 and volume_relative >= 1.3:
            oi_building_early = True
            score += 4
            details.append("OI just starting to build with volume expansion")
    else:
        # Proxy: price + volume co-movement suggests position building
        pct = (today["Close"] / prev["Close"] - 1) * 100
        if abs(pct) < 5 and volume_relative >= 1.4:
            if (price_up and direction == "bullish") or ((not price_up) and direction == "bearish"):
                interpretation = "Proxy: early position building via price + volume"
                oi_building_early = True
                score += 6
                details.append("Volume-led buildup proxy (OI data pending)")
        elif abs(pct) >= 5:
            interpretation = "Move may be late-stage without OI confirmation"
            score += 2

    if direction == "bullish" and "Long buildup" in interpretation:
        score += 3
    if direction == "bearish" and "Short buildup" in interpretation:
        score += 3

    score = min(score, 15.0)
    return FuturesOISignals(
        score=score,
        details=details,
        interpretation=interpretation,
        oi_building_early=oi_building_early,
    )
