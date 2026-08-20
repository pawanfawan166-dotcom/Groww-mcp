"""Format scanner output for display."""

from __future__ import annotations

from scanner.early_momentum_scanner import ScanCandidate


def format_top_candidate(c: ScanCandidate | None) -> str:
    if c is None:
        return "NO TRADE / WAIT FOR TRIGGER — insufficient evidence across F&O universe."

    if c.stage.stage == 1 or (c.stage.stage == 4 and not c.stage.tradeable):
        header = "⚠️ NO TRADE / WAIT FOR TRIGGER"
    else:
        header = "🔥 #1 EARLY EXTREME-MOMENTUM CANDIDATE"

    lines = [
        header,
        "",
        f"Stock: {c.symbol}",
        f"Current Price: ₹{c.current_price}",
        f"Current % Move: {c.pct_move:+.2f}%",
        f"Momentum Stage: Stage {c.stage.stage} — {c.stage.label}",
        f"Catalyst: {c.catalyst or 'None detected'}",
        f"Sector: {c.sector}",
        f"Relative Strength: {c.rs_label}",
        f"Volume / Relative Volume: {c.relative_volume}x vs 20-day avg",
        f"VWAP: {c.vwap_summary}",
        f"PDH: ₹{c.pdh}",
        f"PDL: ₹{c.pdl}",
        f"Opening Range: ₹{c.orl} – ₹{c.orh}",
        f"Futures OI: {c.oi_interpretation}",
        f"OI Interpretation: {c.oi_interpretation}",
        f"Option Chain: {c.option_summary}",
        f"Best CE/PE: {c.best_option}",
        f"Strike: {c.strike if c.strike else 'N/A'}",
        f"Expiry: {c.expiry or 'N/A'}",
        f"Current Premium: ₹{c.premium}" if c.premium else "Current Premium: N/A",
        f"Breakout/Breakdown Level: ₹{c.breakout_level}" if c.breakout_level else "Breakout/Breakdown Level: See PDH/PDL/OR levels",
        f"ENTRY TRIGGER: {c.levels.entry_trigger}",
        f"ENTRY: ₹{c.levels.entry}",
        f"SL: ₹{c.levels.sl}",
        f"T1: ₹{c.levels.t1}",
        f"T2: ₹{c.levels.t2}",
        f"T3: ₹{c.levels.t3}",
        f"Trailing SL: {c.levels.trailing_sl}",
        f"Risk/Reward: {c.levels.risk_reward}",
        f"Extreme Momentum Score: {c.total_score:.1f}/100",
        f"Confidence: {c.confidence}",
        "",
        "Score Breakdown:",
        f"  Catalyst: {c.score.catalyst:.1f}/10",
        f"  Price Structure: {c.score.price_structure:.1f}/15",
        f"  Volume Expansion: {c.score.volume_expansion:.1f}/15",
        f"  VWAP: {c.score.vwap:.1f}/10",
        f"  Relative Strength: {c.score.relative_strength:.1f}/10",
        f"  Futures OI: {c.score.futures_oi:.1f}/15",
        f"  Option Chain: {c.score.option_chain:.1f}/10",
        f"  Sector Momentum: {c.score.sector_momentum:.1f}/5",
        f"  Liquidity: {c.score.liquidity:.1f}/5",
        f"  Risk/Reward: {c.score.risk_reward:.1f}/5",
        "",
        "WHY THIS STOCK COULD BE ENTERING AN EXPANSION PHASE NOW:",
    ]
    for item in c.why:
        lines.append(f"  • {item}")

    lines.extend(
        [
            "",
            "INVALIDATION:",
            f"  • {c.levels.invalidation}",
            "",
            "DISCLAIMER: This stock currently has the strongest early evidence of a potential "
            "extreme-momentum expansion — not a guaranteed outcome.",
        ]
    )
    return "\n".join(lines)


def format_leaderboard(candidates: list[ScanCandidate], n: int = 10) -> str:
    lines = ["Top Early-Momentum Candidates:", ""]
    for i, c in enumerate(candidates[:n], 1):
        lines.append(
            f"{i:2}. {c.symbol:<12} Score:{c.total_score:5.1f}  Stage:{c.stage.stage}  "
            f"Move:{c.pct_move:+5.2f}%  RVOL:{c.relative_volume:.1f}x  {c.stage.label}"
        )
    return "\n".join(lines)
