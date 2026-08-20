"""Convert Groww API responses into scanner-friendly structures."""

from __future__ import annotations

from typing import Any

import pandas as pd


def groww_symbol(exchange: str, trading_symbol: str) -> str:
    return f"{exchange.upper()}_{trading_symbol.upper()}"


def candles_to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    """Normalize Groww / fallback candle payloads to OHLCV DataFrame."""
    candles = payload.get("candles")
    if candles is None and isinstance(payload.get("data"), dict):
        candles = payload["data"].get("candles")
    if candles is None and isinstance(payload.get("data"), list):
        candles = payload["data"]
    if not candles:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for candle in candles:
        if isinstance(candle, dict):
            ts = candle.get("time") or candle.get("timestamp") or candle.get("date")
            rows.append(
                {
                    "Open": float(candle.get("open", candle.get("o", 0))),
                    "High": float(candle.get("high", candle.get("h", 0))),
                    "Low": float(candle.get("low", candle.get("l", 0))),
                    "Close": float(candle.get("close", candle.get("c", 0))),
                    "Volume": float(candle.get("volume", candle.get("v", 0))),
                    "time": ts,
                }
            )
        elif isinstance(candle, (list, tuple)) and len(candle) >= 5:
            rows.append(
                {
                    "time": candle[0],
                    "Open": float(candle[1]),
                    "High": float(candle[2]),
                    "Low": float(candle[3]),
                    "Close": float(candle[4]),
                    "Volume": float(candle[5]) if len(candle) > 5 else 0.0,
                }
            )

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["time"] = pd.to_datetime(frame["time"])
    frame = frame.set_index("time").sort_index()
    return frame


def normalize_option_chain(payload: dict[str, Any], spot: float) -> dict[str, Any]:
    """Convert Groww option chain into NSE-like records format for signal modules."""
    chain = payload.get("option_chain", payload)
    if not chain:
        return {}

    # Groww live format may use strikes dict
    strikes_map = chain.get("strikes")
    if isinstance(strikes_map, dict):
        data = []
        for strike_key, legs in strikes_map.items():
            ce = legs.get("CE") or {}
            pe = legs.get("PE") or {}
            data.append(
                {
                    "strikePrice": float(strike_key),
                    "CE": _normalize_leg(ce),
                    "PE": _normalize_leg(pe),
                }
            )
        expiry = chain.get("expiry_date") or chain.get("expiry")
        return {
            "records": {
                "underlyingValue": chain.get("underlying_ltp", spot),
                "expiryDates": [expiry] if expiry else [],
                "data": sorted(data, key=lambda x: x["strikePrice"]),
            },
            "price_source": payload.get("price_source", "groww"),
        }

    # Already NSE-like
    if "records" in chain:
        return chain

    # List of contracts
    contracts = chain.get("contracts") or chain.get("data")
    if isinstance(contracts, list) and contracts:
        by_strike: dict[float, dict[str, Any]] = {}
        for row in contracts:
            strike = float(row.get("strike") or row.get("strikePrice") or 0)
            if not strike:
                continue
            bucket = by_strike.setdefault(strike, {"strikePrice": strike, "CE": {}, "PE": {}})
            opt_type = str(row.get("option_type") or row.get("instrument_type") or "").upper()
            leg = _normalize_leg(row)
            if opt_type in {"CE", "CALL"}:
                bucket["CE"] = leg
            elif opt_type in {"PE", "PUT"}:
                bucket["PE"] = leg
        return {
            "records": {
                "underlyingValue": chain.get("underlying_ltp", spot),
                "expiryDates": [chain.get("expiry_date")] if chain.get("expiry_date") else [],
                "data": sorted(by_strike.values(), key=lambda x: x["strikePrice"]),
            },
            "price_source": payload.get("price_source", "groww"),
        }

    return {}


def _normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    if not leg:
        return {}
    return {
        "strikePrice": leg.get("strikePrice") or leg.get("strike"),
        "lastPrice": leg.get("lastPrice") or leg.get("ltp") or leg.get("last_price"),
        "openInterest": leg.get("openInterest") or leg.get("open_interest") or leg.get("oi"),
        "changeinOpenInterest": leg.get("changeinOpenInterest")
        or leg.get("change_in_oi")
        or leg.get("oi_change")
        or leg.get("change_in_open_interest"),
        "totalTradedVolume": leg.get("totalTradedVolume")
        or leg.get("volume")
        or leg.get("traded_volume"),
        "expiryDate": leg.get("expiryDate") or leg.get("expiry") or leg.get("expiry_date"),
    }
