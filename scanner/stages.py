"""Momentum stage classification."""

from __future__ import annotations

from dataclasses import dataclass

from scanner.signals.price_action import PriceActionSignals
from scanner.signals.volume import VolumeSignals


@dataclass
class MomentumStage:
    stage: int
    label: str
    tradeable: bool
    reason: str


def classify_stage(
    pct_move: float,
    price: PriceActionSignals,
    volume: VolumeSignals,
    total_score: float,
) -> MomentumStage:
    abs_move = abs(pct_move)

    if abs_move >= 10 or (abs_move >= 7 and not price.compression and not price.range_expansion):
        return MomentumStage(
            stage=4,
            label="Extended",
            tradeable=False,
            reason="Move already excessive; chasing risk elevated",
        )

    if price.compression and abs_move < 2 and volume.relative_volume < 1.5:
        return MomentumStage(
            stage=1,
            label="Early / Compression",
            tradeable=False,
            reason="Building base; wait for trigger",
        )

    trigger = (
        (price.breakout_level or price.breakdown_level)
        and volume.relative_volume >= 1.3
        and (price.range_expansion or price.near_key_level)
    )

    if trigger and abs_move < 5:
        return MomentumStage(
            stage=2,
            label="Trigger",
            tradeable=True,
            reason="Breakout/breakdown with early volume confirmation",
        )

    if 3 <= abs_move < 8 and volume.relative_volume >= 1.5 and total_score >= 45:
        return MomentumStage(
            stage=3,
            label="Expansion",
            tradeable=True,
            reason="Momentum accelerating with multi-signal confirmation",
        )

    if abs_move >= 8:
        return MomentumStage(
            stage=4,
            label="Extended",
            tradeable=False,
            reason="Late-stage move",
        )

    if price.compression:
        return MomentumStage(stage=1, label="Early / Compression", tradeable=False, reason="Compression without trigger")

    return MomentumStage(stage=2, label="Trigger", tradeable=total_score >= 40, reason="Emerging trigger setup")
