"""Option chain early positioning signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OptionSignals:
    score: float
    details: list[str]
    best_option: str
    strike: float | None
    expiry: str | None
    premium: float | None
    pcr_change: str


def _nearest_atm_strike(strikes: list[float], spot: float) -> float:
    return min(strikes, key=lambda s: abs(s - spot))


def analyze_options(option_chain: dict, direction: str, spot: float) -> OptionSignals:
    details: list[str] = []
    score = 0.0
    best_option = "N/A"
    strike: float | None = None
    expiry: str | None = None
    premium: float | None = None
    pcr_change = "unknown"

    records = option_chain.get("records", {}) if option_chain else {}
    data = records.get("data", [])
    expiries = records.get("expiryDates", [])

    if not data:
        return OptionSignals(
            score=2.0,
            details=["Option chain unavailable — market closed or data pending"],
            best_option="N/A",
            strike=None,
            expiry=expiries[0] if expiries else None,
            premium=None,
            pcr_change="unknown",
        )

    strikes = [float(row.get("strikePrice", 0)) for row in data if row.get("strikePrice")]
    if not strikes:
        return OptionSignals(score=2.0, details=["No strikes in option chain"], best_option="N/A", strike=None, expiry=None, premium=None, pcr_change="unknown")

    atm = _nearest_atm_strike(strikes, spot)
    atm_row = next((row for row in data if float(row.get("strikePrice", 0)) == atm), data[len(data) // 2])

    ce = atm_row.get("CE") or {}
    pe = atm_row.get("PE") or {}
    ce_oi_chg = float(ce.get("changeinOpenInterest") or 0)
    pe_oi_chg = float(pe.get("changeinOpenInterest") or 0)
    ce_vol = float(ce.get("totalTradedVolume") or 0)
    pe_vol = float(pe.get("totalTradedVolume") or 0)

    total_ce_oi = sum(float((row.get("CE") or {}).get("openInterest") or 0) for row in data)
    total_pe_oi = sum(float((row.get("PE") or {}).get("openInterest") or 0) for row in data)
    pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
    pcr_change = "bullish" if pcr < 0.9 else "bearish" if pcr > 1.1 else "neutral"

    if direction == "bullish":
        best_option = "CE"
        leg = ce
        if ce_vol > pe_vol * 1.2:
            score += 3
            details.append("ATM/near-ATM CE volume surging")
        if ce_oi_chg > 0 and ce_oi_chg > pe_oi_chg:
            score += 3
            details.append("CE OI building supports bullish direction")
        if pcr < 1.0:
            score += 2
            details.append("PCR shifting lower (bullish positioning)")
    else:
        best_option = "PE"
        leg = pe
        if pe_vol > ce_vol * 1.2:
            score += 3
            details.append("ATM/near-ATM PE volume surging")
        if pe_oi_chg > 0 and pe_oi_chg > ce_oi_chg:
            score += 3
            details.append("PE OI building supports bearish direction")
        if pcr > 1.0:
            score += 2
            details.append("PCR shifting higher (bearish positioning)")

    strike = float(leg.get("strikePrice") or atm)
    premium = float(leg.get("lastPrice") or leg.get("ltp") or 0) or None
    expiry = expiries[0] if expiries else leg.get("expiryDate")

    # Premium expansion beginning (not already extreme)
    if premium and premium < spot * 0.03:
        score += 2
        details.append("Option premium expansion beginning (not extended)")

    score = min(score, 10.0)
    return OptionSignals(
        score=score,
        details=details,
        best_option=best_option,
        strike=strike,
        expiry=expiry,
        premium=premium,
        pcr_change=pcr_change,
    )
