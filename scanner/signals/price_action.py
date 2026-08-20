"""Price action signal detection for early momentum."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PriceActionSignals:
    score: float
    details: list[str]
    pdh: float
    pdl: float
    orh: float
    orl: float
    compression: bool
    breakout_level: float | None
    breakdown_level: float | None
    direction: str
    range_expansion: bool
    near_key_level: bool


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyze_price_action(daily: pd.DataFrame, intraday: pd.DataFrame) -> PriceActionSignals:
    details: list[str] = []
    score = 0.0

    prev = daily.iloc[-2]
    today = daily.iloc[-1]
    pdh = float(prev["High"])
    pdl = float(prev["Low"])
    close = float(today["Close"])
    open_price = float(today["Opening"] if "Opening" in today else today["Open"])

    if not intraday.empty:
        day_bars = intraday[intraday.index.date == intraday.index[-1].date()]
        if day_bars.empty:
            day_bars = intraday.tail(75)
        or_window = day_bars.head(6) if len(day_bars) >= 6 else day_bars
        orh = float(or_window["High"].max())
        orl = float(or_window["Low"].min())
    else:
        orh = float(today["High"])
        orl = float(today["Low"])

    # Compression: ATR contraction over last 5 sessions vs prior 10
    atr = _atr(daily)
    recent_atr = float(atr.iloc[-5:].mean())
    prior_atr = float(atr.iloc[-15:-5].mean()) if len(atr) >= 15 else recent_atr
    compression = prior_atr > 0 and recent_atr / prior_atr < 0.8
    if compression:
        score += 4
        details.append("Tight consolidation / ATR compression")

    # Narrow range candles
    recent_ranges = (daily["High"] - daily["Low"]).iloc[-5:]
    hist_ranges = (daily["High"] - daily["Low"]).iloc[-25:-5]
    if len(hist_ranges) > 0 and recent_ranges.mean() < hist_ranges.mean() * 0.75:
        score += 2
        details.append("Narrow-range candles")

    # Higher lows / lower highs
    lows = daily["Low"].iloc[-6:]
    highs = daily["High"].iloc[-6:]
    higher_lows = all(lows.iloc[i] >= lows.iloc[i - 1] * 0.998 for i in range(1, len(lows)))
    lower_highs = all(highs.iloc[i] <= highs.iloc[i - 1] * 1.002 for i in range(1, len(highs)))
    if higher_lows:
        score += 2
        details.append("Higher lows forming")
    if lower_highs:
        score += 2
        details.append("Lower highs forming")

    # Proximity to key levels (within 0.6%)
    def near(level: float) -> bool:
        return abs(close - level) / max(level, 1) <= 0.006

    near_key_level = any(near(x) for x in [pdh, pdl, orh, orl])
    if near(pdh) or near(orh):
        score += 2
        details.append("Price approaching PDH/ORH")
    if near(pdl) or near(orl):
        score += 2
        details.append("Price approaching PDL/ORL")

    direction = "bullish" if close >= open_price else "bearish"
    breakout_level = None
    breakdown_level = None
    consolidation_high = float(daily["High"].iloc[-8:-1].max())
    consolidation_low = float(daily["Low"].iloc[-8:-1].min())

    if close > consolidation_high * 1.001:
        breakout_level = consolidation_high
        direction = "bullish"
        score += 3
        details.append("Fresh breakout from consolidation")
    elif close < consolidation_low * 0.999:
        breakdown_level = consolidation_low
        direction = "bearish"
        score += 3
        details.append("Fresh breakdown from consolidation")

    # Range expansion after compression
    today_range = float(today["High"] - today["Low"])
    avg_range = float((daily["High"] - daily["Low"]).iloc[-10:-1].mean())
    range_expansion = compression and today_range > avg_range * 1.2
    if range_expansion:
        score += 2
        details.append("Candle range expanding after compression")

    # Penalize if move already extended on daily
    pct_move = (close / float(prev["Close"]) - 1) * 100
    if abs(pct_move) > 8:
        score -= 4
        details.append("Daily move already extended — early edge reduced")

    score = float(np.clip(score, 0, 15))
    return PriceActionSignals(
        score=score,
        details=details,
        pdh=pdh,
        pdl=pdl,
        orh=orh,
        orl=orl,
        compression=compression,
        breakout_level=breakout_level,
        breakdown_level=breakdown_level,
        direction=direction,
        range_expansion=range_expansion,
        near_key_level=near_key_level,
    )
