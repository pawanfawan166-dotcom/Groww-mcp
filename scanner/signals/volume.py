"""Volume expansion signal detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VolumeSignals:
    score: float
    details: list[str]
    relative_volume: float
    volume_expanding: bool
    volume_confirms_price: bool


def analyze_volume(daily: pd.DataFrame, intraday: pd.DataFrame, direction: str) -> VolumeSignals:
    details: list[str] = []
    score = 0.0

    avg_vol = float(daily["Volume"].iloc[-21:-1].mean())
    today_vol = float(daily["Volume"].iloc[-1])
    relative_volume = today_vol / avg_vol if avg_vol > 0 else 1.0

    if relative_volume >= 2.0:
        score += 6
        details.append(f"Relative volume {relative_volume:.1f}x (>2x)")
    elif relative_volume >= 1.5:
        score += 4
        details.append(f"Relative volume {relative_volume:.1f}x (elevated)")
    elif relative_volume >= 1.2:
        score += 2
        details.append(f"Relative volume {relative_volume:.1f}x (building)")

    # Volume before/at breakout: compare first half vs second half intraday
    volume_expanding = False
    if not intraday.empty and len(intraday) >= 20:
        mid = len(intraday) // 2
        first_half = float(intraday["Volume"].iloc[:mid].sum())
        second_half = float(intraday["Volume"].iloc[mid:].sum())
        if second_half > first_half * 1.15:
            volume_expanding = True
            score += 3
            details.append("Intraday volume expanding into session")

    # Consecutive high-volume candles on daily
    vol_threshold = avg_vol * 1.3
    recent = daily["Volume"].iloc[-4:]
    if (recent > vol_threshold).sum() >= 2:
        score += 3
        details.append("Multiple consecutive high-volume sessions")

    # Volume confirms price
    today = daily.iloc[-1]
    price_up = today["Close"] > today["Open"]
    volume_confirms_price = (price_up and direction == "bullish") or ((not price_up) and direction == "bearish")
    if volume_confirms_price and relative_volume >= 1.2:
        score += 3
        details.append("Volume confirming price direction")
    elif not volume_confirms_price and relative_volume < 1.1:
        score -= 2
        details.append("Price moving without meaningful volume")

    score = float(np.clip(score, 0, 15))
    return VolumeSignals(
        score=score,
        details=details,
        relative_volume=relative_volume,
        volume_expanding=volume_expanding,
        volume_confirms_price=volume_confirms_price,
    )
