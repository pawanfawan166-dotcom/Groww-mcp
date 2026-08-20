"""VWAP-based signal detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VwapSignals:
    score: float
    details: list[str]
    vwap: float
    price_vs_vwap: str
    vwap_trend: str


def _compute_vwap(bars: pd.DataFrame) -> pd.Series:
    typical = (bars["High"] + bars["Low"] + bars["Close"]) / 3
    cum_vol = bars["Volume"].cumsum()
    cum_pv = (typical * bars["Volume"]).cumsum()
    return cum_pv / cum_vol.replace(0, np.nan)


def analyze_vwap(intraday: pd.DataFrame, daily: pd.DataFrame, direction: str) -> VwapSignals:
    details: list[str] = []
    score = 0.0

    if intraday.empty:
        close = float(daily["Close"].iloc[-1])
        return VwapSignals(
            score=2.0,
            details=["Intraday VWAP unavailable — using daily proxy"],
            vwap=close,
            price_vs_vwap="unknown",
            vwap_trend="flat",
        )

    day_bars = intraday[intraday.index.date == intraday.index[-1].date()]
    if day_bars.empty:
        day_bars = intraday.tail(75)

    vwap_series = _compute_vwap(day_bars)
    vwap = float(vwap_series.iloc[-1])
    close = float(day_bars["Close"].iloc[-1])

    if direction == "bullish":
        if close > vwap:
            score += 3
            details.append("Price above VWAP")
        if close > vwap and day_bars["Low"].iloc[-3:].min() >= vwap * 0.998:
            score += 3
            details.append("Pullback respecting VWAP support")
        if len(vwap_series) >= 10 and vwap_series.iloc[-1] > vwap_series.iloc[-10]:
            score += 2
            details.append("VWAP trending upward")
        if day_bars["Close"].iloc[0] < vwap and close > vwap:
            score += 2
            details.append("Fresh VWAP cross (bullish)")
        price_vs_vwap = "above" if close > vwap else "below"
        vwap_trend = "up" if vwap_series.iloc[-1] > vwap_series.iloc[max(0, len(vwap_series) - 10)] else "down"
    else:
        if close < vwap:
            score += 3
            details.append("Price below VWAP")
        if close < vwap and day_bars["High"].iloc[-3:].max() <= vwap * 1.002:
            score += 3
            details.append("Retest failing at VWAP resistance")
        if len(vwap_series) >= 10 and vwap_series.iloc[-1] < vwap_series.iloc[-10]:
            score += 2
            details.append("VWAP trending downward")
        if day_bars["Close"].iloc[0] > vwap and close < vwap:
            score += 2
            details.append("Fresh VWAP cross (bearish)")
        price_vs_vwap = "below" if close < vwap else "above"
        vwap_trend = "down" if vwap_series.iloc[-1] < vwap_series.iloc[max(0, len(vwap_series) - 10)] else "up"

    score = float(np.clip(score, 0, 10))
    return VwapSignals(
        score=score,
        details=details,
        vwap=vwap,
        price_vs_vwap=price_vs_vwap,
        vwap_trend=vwap_trend,
    )
