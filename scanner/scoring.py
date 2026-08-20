"""Extreme momentum scoring and trade level generation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from scanner.signals.catalyst import CatalystSignals
from scanner.signals.futures_oi import FuturesOISignals
from scanner.signals.options import OptionSignals
from scanner.signals.price_action import PriceActionSignals
from scanner.signals.relative_strength import RelativeStrengthSignals
from scanner.signals.volume import VolumeSignals
from scanner.signals.vwap import VwapSignals
from scanner.stages import MomentumStage


@dataclass
class ScoreBreakdown:
    catalyst: float
    price_structure: float
    volume_expansion: float
    vwap: float
    relative_strength: float
    futures_oi: float
    option_chain: float
    sector_momentum: float
    liquidity: float
    risk_reward: float

    @property
    def total(self) -> float:
        return (
            self.catalyst
            + self.price_structure
            + self.volume_expansion
            + self.vwap
            + self.relative_strength
            + self.futures_oi
            + self.option_chain
            + self.sector_momentum
            + self.liquidity
            + self.risk_reward
        )


@dataclass
class TradeLevels:
    entry_trigger: str
    entry: float
    sl: float
    t1: float
    t2: float
    t3: float
    trailing_sl: str
    risk_reward: str
    invalidation: str


def score_sector_momentum(sector_return: float | None, direction: str) -> float:
    if sector_return is None:
        return 2.0
    if direction == "bullish" and sector_return > 0.5:
        return 5.0
    if direction == "bearish" and sector_return < -0.5:
        return 5.0
    if abs(sector_return) < 0.3:
        return 3.0
    return 2.0


def score_liquidity(daily: pd.DataFrame, avg_volume_quote: float | None) -> float:
    avg_vol = float(daily["Volume"].iloc[-20:].mean())
    turnover_proxy = avg_vol * float(daily["Close"].iloc[-1])
    if turnover_proxy > 50_000_000:
        return 5.0
    if turnover_proxy > 20_000_000:
        return 4.0
    if turnover_proxy > 5_000_000:
        return 3.0
    return 1.0


def score_risk_reward(
    close: float,
    sl: float,
    t1: float,
    direction: str,
) -> float:
    risk = abs(close - sl)
    reward = abs(t1 - close)
    if risk <= 0:
        return 1.0
    rr = reward / risk
    if rr >= 2.5:
        return 5.0
    if rr >= 2.0:
        return 4.0
    if rr >= 1.5:
        return 3.0
    return 1.0


def build_trade_levels(
    daily: pd.DataFrame,
    price: PriceActionSignals,
    direction: str,
    stage: MomentumStage,
) -> TradeLevels:
    close = float(daily["Close"].iloc[-1])
    atr = float((daily["High"] - daily["Low"]).iloc[-10:].mean())

    if direction == "bullish":
        breakout = price.breakout_level or price.pdh
        # Prefer retest entry when price already cleared the breakout (early expansion, not chase)
        if breakout and close > breakout * 1.01:
            entry = breakout
            entry_trigger = f"Retest hold above {breakout:.2f} with volume > 1.5x on 5-min close"
        else:
            entry = max(close, breakout * 1.001) if breakout else close
            entry_trigger = f"Hold above {breakout:.2f} with volume > 1.5x on 5-min close"
        sl = min(price.orl, price.pdl, entry - atr * 0.8)
        t1 = entry + atr * 1.2
        t2 = entry + atr * 2.2
        t3 = entry + atr * 3.5
        invalidation = f"5-min close below VWAP and below {sl:.2f}"
        trailing = "Trail below last 15-min swing low or VWAP after T1"
    else:
        breakdown = price.breakdown_level or price.pdl
        if breakdown and close < breakdown * 0.99:
            entry = breakdown
            entry_trigger = f"Retest rejection below {breakdown:.2f} with rising volume"
        else:
            entry = min(close, breakdown * 0.999) if breakdown else close
            entry_trigger = f"Break below {breakdown:.2f} with rising volume on 5-min close"
        sl = max(price.orh, price.pdh, entry + atr * 0.8)
        t1 = entry - atr * 1.2
        t2 = entry - atr * 2.2
        t3 = entry - atr * 3.5
        invalidation = f"5-min close above VWAP and above {sl:.2f}"
        trailing = "Trail above last 15-min swing high or VWAP after T1"

    if stage.stage == 1:
        entry_trigger = "WAIT — compression building, no trigger yet"

    risk = abs(entry - sl)
    reward = abs(t1 - entry)
    rr_ratio = reward / risk if risk > 0 else 0
    rr = score_risk_reward(entry, sl, t1, direction)
    rr_label = f"1:{rr_ratio:.1f}" if rr_ratio >= 1 else f"1:{rr_ratio:.1f} (tighten SL or wait for retest)"

    return TradeLevels(
        entry_trigger=entry_trigger,
        entry=round(entry, 2),
        sl=round(sl, 2),
        t1=round(t1, 2),
        t2=round(t2, 2),
        t3=round(t3, 2),
        trailing_sl=trailing,
        risk_reward=rr_label,
        invalidation=invalidation,
    )


def compute_score(
    daily: pd.DataFrame,
    catalyst: CatalystSignals,
    price: PriceActionSignals,
    volume: VolumeSignals,
    vwap: VwapSignals,
    rs: RelativeStrengthSignals,
    futures_oi: FuturesOISignals,
    options: OptionSignals,
    sector_return: float | None,
    direction: str,
) -> ScoreBreakdown:
    liquidity = score_liquidity(daily, None)
    levels = build_trade_levels(
        daily,
        price,
        direction,
        MomentumStage(stage=2, label="Trigger", tradeable=True, reason=""),
    )
    rr = score_risk_reward(float(daily["Close"].iloc[-1]), levels.sl, levels.t1, direction)

    return ScoreBreakdown(
        catalyst=catalyst.score,
        price_structure=price.score,
        volume_expansion=volume.score,
        vwap=vwap.score,
        relative_strength=rs.score,
        futures_oi=futures_oi.score,
        option_chain=options.score,
        sector_momentum=score_sector_momentum(sector_return, direction),
        liquidity=liquidity,
        risk_reward=rr,
    )


def confidence_label(total: float, stage: MomentumStage, tradeable: bool) -> str:
    if not tradeable or stage.stage in (1, 4):
        return "LOW — NO TRADE / WAIT FOR TRIGGER"
    if total >= 70:
        return "HIGH"
    if total >= 55:
        return "MEDIUM"
    return "LOW"
