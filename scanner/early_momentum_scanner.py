"""Main early extreme-momentum scanner."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from scanner.data_provider import MarketDataProvider, MarketSnapshot
from scanner.scoring import (
    ScoreBreakdown,
    TradeLevels,
    build_trade_levels,
    compute_score,
    confidence_label,
)
from scanner.signals.catalyst import analyze_catalysts
from scanner.signals.futures_oi import analyze_futures_oi
from scanner.signals.options import analyze_options
from scanner.signals.price_action import analyze_price_action
from scanner.signals.relative_strength import analyze_relative_strength
from scanner.signals.volume import analyze_volume
from scanner.signals.vwap import analyze_vwap
from scanner.stages import MomentumStage, classify_stage
from scanner.universe import load_fno_symbols, sector_for

logger = logging.getLogger(__name__)


@dataclass
class ScanCandidate:
    symbol: str
    current_price: float
    pct_move: float
    stage: MomentumStage
    sector: str
    catalyst: str | None
    rs_label: str
    relative_volume: float
    vwap_summary: str
    pdh: float
    pdl: float
    orh: float
    orl: float
    oi_interpretation: str
    option_summary: str
    best_option: str
    strike: float | None
    expiry: str | None
    premium: float | None
    breakout_level: float | None
    levels: TradeLevels
    score: ScoreBreakdown
    confidence: str
    why: list[str] = field(default_factory=list)
    signal_details: dict[str, list[str]] = field(default_factory=dict)

    @property
    def total_score(self) -> float:
        return self.score.total


class EarlyMomentumScanner:
    """Scan NSE F&O universe for early extreme-momentum setups."""

    def __init__(self, max_workers: int = 3) -> None:
        self.provider = MarketDataProvider()
        self.max_workers = max_workers

    def scan(self, symbols: list[str] | None = None, limit: int | None = None) -> list[ScanCandidate]:
        universe = symbols or load_fno_symbols()
        if limit:
            universe = universe[:limit]

        # Prefetch benchmark before parallel symbol fetches
        nifty = self.provider.get_nifty_daily()

        snapshots: dict[str, MarketSnapshot] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self.provider.fetch_snapshot, sym, sector_for(sym)): sym for sym in universe
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    snap = future.result()
                    if snap:
                        snapshots[sym] = snap
                except Exception as exc:
                    logger.warning("Failed %s: %s", sym, exc)

        sector_returns = self.provider.batch_sector_returns(snapshots)
        candidates: list[ScanCandidate] = []

        for sym, snap in snapshots.items():
            candidate = self._evaluate(snap, nifty, sector_returns.get(snap.sector))
            if candidate:
                candidates.append(candidate)

        # Rank by early-signal score, penalize stage 4, boost stage 2
        def rank_key(c: ScanCandidate) -> float:
            bonus = 5 if c.stage.stage == 2 else 2 if c.stage.stage == 3 else -10 if c.stage.stage == 4 else -5
            return c.total_score + bonus

        candidates.sort(key=rank_key, reverse=True)
        return candidates

    def _evaluate(
        self,
        snap: MarketSnapshot,
        nifty,
        sector_return: float | None,
    ) -> ScanCandidate | None:
        daily = snap.daily
        intraday = snap.intraday
        if len(daily) < 15:
            return None

        price = analyze_price_action(daily, intraday)
        volume = analyze_volume(daily, intraday, price.direction)
        vwap = analyze_vwap(intraday, daily, price.direction)
        catalyst = analyze_catalysts(snap.catalysts)
        rs = analyze_relative_strength(daily, nifty, sector_return, price.direction)
        futures_oi = analyze_futures_oi(daily, snap.option_chain, price.direction, volume.relative_volume)
        options = analyze_options(snap.option_chain, price.direction, float(daily["Close"].iloc[-1]))

        score = compute_score(
            daily, catalyst, price, volume, vwap, rs, futures_oi, options, sector_return, price.direction
        )
        close = float(daily["Close"].iloc[-1])
        prev_close = float(daily["Close"].iloc[-2])
        pct_move = (close / prev_close - 1) * 100

        stage = classify_stage(pct_move, price, volume, score.total)
        levels = build_trade_levels(daily, price, price.direction, stage)
        confidence = confidence_label(score.total, stage, stage.tradeable)

        why = [
            *price.details[:3],
            *volume.details[:2],
            *vwap.details[:2],
            *futures_oi.details[:1],
        ]

        breakout = price.breakout_level or price.breakdown_level
        return ScanCandidate(
            symbol=snap.symbol,
            current_price=round(close, 2),
            pct_move=round(pct_move, 2),
            stage=stage,
            sector=snap.sector,
            catalyst=catalyst.primary_catalyst,
            rs_label=rs.label,
            relative_volume=round(volume.relative_volume, 2),
            vwap_summary=f"{vwap.price_vs_vwap} VWAP ({vwap.vwap_trend}) @ {vwap.vwap:.2f}",
            pdh=round(price.pdh, 2),
            pdl=round(price.pdl, 2),
            orh=round(price.orh, 2),
            orl=round(price.orl, 2),
            oi_interpretation=futures_oi.interpretation,
            option_summary="; ".join(options.details[:2]) if options.details else "N/A",
            best_option=options.best_option,
            strike=options.strike,
            expiry=options.expiry,
            premium=options.premium,
            breakout_level=round(breakout, 2) if breakout else None,
            levels=levels,
            score=score,
            confidence=confidence,
            why=why,
            signal_details={
                "price": price.details,
                "volume": volume.details,
                "vwap": vwap.details,
                "catalyst": catalyst.details,
                "rs": rs.details,
                "oi": futures_oi.details,
                "options": options.details,
            },
        )

    def top_candidate(self, candidates: list[ScanCandidate]) -> ScanCandidate | None:
        tradeable = [c for c in candidates if c.stage.tradeable and c.stage.stage in (2, 3)]
        if tradeable:
            return tradeable[0]
        return candidates[0] if candidates else None
