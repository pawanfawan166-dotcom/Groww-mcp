from __future__ import annotations

import math
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any


def _yahoo_symbol(trading_symbol: str, exchange: str = "NSE") -> str:
    sym = trading_symbol.upper()
    index_map = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    }
    commodity_map = {
        "CRUDEOIL": "CL=F",
        "CRUDEOILM": "CL=F",
        "NATURALGAS": "NG=F",
        "GOLD": "GC=F",
        "SILVER": "SI=F",
    }
    if sym in index_map:
        return index_map[sym]
    if sym in commodity_map:
        return commodity_map[sym]
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return f"{sym}{suffix}"


def _commodity_inr_scale(symbol: str) -> float:
    """Scale global futures price to approximate MCX INR quote."""
    scales = {
        "CRUDEOIL": 95.0,
        "CRUDEOILM": 95.0,
        "NATURALGAS": 30.0,
        "GOLD": 2800.0,
        "SILVER": 85.0,
    }
    return scales.get(symbol.upper(), 1.0)


def _ticker(trading_symbol: str, exchange: str = "NSE"):
    import yfinance as yf

    return yf.Ticker(_yahoo_symbol(trading_symbol, exchange))


def _scaled_price(trading_symbol: str, exchange: str, raw: float) -> float:
    if exchange.upper() == "MCX" or trading_symbol.upper() in {"CRUDEOIL", "CRUDEOILM", "NATURALGAS", "GOLD", "SILVER"}:
        return raw * _commodity_inr_scale(trading_symbol)
    return raw


def fetch_ltp(trading_symbol: str, exchange: str = "NSE") -> float:
    """Fetch LTP from Yahoo Finance when Groww market-data APIs are unavailable."""
    raw = _raw_price(trading_symbol, exchange)
    return _scaled_price(trading_symbol, exchange, raw)


def _raw_price(trading_symbol: str, exchange: str) -> float:
    ticker = _ticker(trading_symbol, exchange)
    info = ticker.fast_info
    ltp = info.get("last_price") or info.get("lastPrice")
    if ltp:
        return float(ltp)
    hist = ticker.history(period="1d")
    if hist.empty:
        raise ValueError(f"No market data found for {trading_symbol} on {exchange}.")
    return float(hist["Close"].iloc[-1])


def fetch_quote(trading_symbol: str, exchange: str = "NSE") -> dict[str, Any]:
    """Fetch quote-like data from Yahoo Finance."""
    ticker = _ticker(trading_symbol, exchange)
    info = ticker.fast_info
    hist = ticker.history(period="5d")

    last_price = info.get("last_price") or info.get("lastPrice")
    if not last_price and not hist.empty:
        last_price = float(hist["Close"].iloc[-1])
    if not last_price:
        raise ValueError(f"No quote data found for {trading_symbol} on {exchange}.")

    last_price = _scaled_price(trading_symbol, exchange, float(last_price))
    prev_close = float(info.get("previous_close") or info.get("previousClose") or 0)
    if not prev_close and len(hist) > 1:
        prev_close = float(hist["Close"].iloc[-2])
    prev_close = _scaled_price(trading_symbol, exchange, prev_close) if prev_close else 0.0

    day_change = last_price - prev_close if prev_close else 0.0
    day_change_perc = (day_change / prev_close * 100) if prev_close else 0.0

    ohlc = {}
    if not hist.empty:
        today = hist.iloc[-1]
        scale = _commodity_inr_scale(trading_symbol) if trading_symbol.upper() in {"CRUDEOIL", "CRUDEOILM"} else 1.0
        if exchange.upper() == "MCX":
            scale = _commodity_inr_scale(trading_symbol)
        ohlc = {
            "open": float(today["Open"]) * scale,
            "high": float(today["High"]) * scale,
            "low": float(today["Low"]) * scale,
            "close": float(today["Close"]) * scale,
        }

    return {
        "last_price": round(last_price, 2),
        "day_change": round(day_change, 2),
        "day_change_perc": round(day_change_perc, 2),
        "volume": int(info.get("last_volume") or info.get("lastVolume") or 0),
        "ohlc": ohlc,
    }


def fetch_ohlc(trading_symbol: str, exchange: str = "NSE") -> dict[str, float]:
    """Fetch OHLC from Yahoo Finance."""
    hist = _ticker(trading_symbol, exchange).history(period="5d")
    if hist.empty:
        raise ValueError(f"No OHLC data found for {trading_symbol} on {exchange}.")
    row = hist.iloc[-1]
    scale = _commodity_inr_scale(trading_symbol) if exchange.upper() == "MCX" else 1.0
    if trading_symbol.upper() in {"CRUDEOIL", "CRUDEOILM", "NATURALGAS", "GOLD", "SILVER"}:
        scale = _commodity_inr_scale(trading_symbol)
    return {
        "open": round(float(row["Open"]) * scale, 2),
        "high": round(float(row["High"]) * scale, 2),
        "low": round(float(row["Low"]) * scale, 2),
        "close": round(float(row["Close"]) * scale, 2),
    }


def _yf_interval(candle_interval: str) -> tuple[str, str]:
    mapping = {
        "1minute": ("1m", "5d"),
        "5minute": ("5m", "1mo"),
        "15minute": ("15m", "1mo"),
        "30minute": ("30m", "1mo"),
        "1hour": ("1h", "3mo"),
        "1day": ("1d", "1y"),
        "1week": ("1wk", "2y"),
        "1month": ("1mo", "5y"),
    }
    return mapping.get(candle_interval, ("1d", "1y"))


def fetch_historical_candles(
    trading_symbol: str,
    exchange: str,
    start_time: str,
    end_time: str,
    candle_interval: str = "1day",
) -> dict[str, Any]:
    interval, _ = _yf_interval(candle_interval)
    start = datetime.strptime(start_time[:10], "%Y-%m-%d")
    end = datetime.strptime(end_time[:10], "%Y-%m-%d")
    hist = _ticker(trading_symbol, exchange).history(start=start, end=end + timedelta(days=1), interval=interval)
    if hist.empty:
        raise ValueError(f"No historical data for {trading_symbol}.")

    scale = _commodity_inr_scale(trading_symbol) if trading_symbol.upper() in {"CRUDEOIL", "CRUDEOILM"} or exchange.upper() == "MCX" else 1.0
    candles = []
    for ts, row in hist.iterrows():
        candles.append(
            {
                "time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "open": round(float(row["Open"]) * scale, 2),
                "high": round(float(row["High"]) * scale, 2),
                "low": round(float(row["Low"]) * scale, 2),
                "close": round(float(row["Close"]) * scale, 2),
                "volume": int(row["Volume"]),
            }
        )
    return {"candles": candles, "count": len(candles)}


def _last_tuesday_of_month(year: int, month: int) -> date:
    last_day = monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() != 1:
        d -= timedelta(days=1)
    return d


def _weekly_tuesdays(from_date: date, count: int = 8) -> list[date]:
    d = from_date
    while d.weekday() != 1:
        d += timedelta(days=1)
    out = []
    for _ in range(count):
        out.append(d)
        d += timedelta(days=7)
    return out


def fetch_expiries(
    underlying_symbol: str,
    exchange: str = "NSE",
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    today = date.today()
    year = year or today.year
    under = underlying_symbol.upper()

    if under in {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}:
        weekly = _weekly_tuesdays(today, 8)
        monthly = [_last_tuesday_of_month(year, m) for m in range(1, 13) if _last_tuesday_of_month(year, m) >= today]
        expiries = sorted({d.isoformat() for d in weekly + monthly})
    elif under in {"CRUDEOIL", "CRUDEOILM", "NATURALGAS", "GOLD", "SILVER"}:
        expiries = []
        for m in range(today.month, 13):
            expiries.append(_last_tuesday_of_month(year, m).isoformat())
        if year == today.year:
            expiries = [e for e in expiries if e >= today.isoformat()]
    else:
        expiries = [_last_tuesday_of_month(year, m).isoformat() for m in range(1, 13)]
        expiries = [e for e in expiries if e >= today.isoformat()]

    if month:
        expiries = [e for e in expiries if int(e[5:7]) == month]

    return {"underlying_symbol": under, "exchange": exchange.upper(), "expiries": expiries[:12]}


def _strike_step(underlying: str, spot: float) -> int:
    under = underlying.upper()
    if under == "NIFTY":
        return 50
    if under == "BANKNIFTY":
        return 100
    if under in {"CRUDEOIL", "CRUDEOILM"}:
        return 50 if spot > 5000 else 10
    if spot < 500:
        return 5
    if spot < 2000:
        return 10
    return 50


def fetch_contracts(
    underlying_symbol: str,
    expiry_date: str,
    exchange: str = "NSE",
    strikes_each_side: int = 5,
) -> dict[str, Any]:
    spot = fetch_ltp(underlying_symbol, exchange)
    step = _strike_step(underlying_symbol, spot)
    atm = round(spot / step) * step
    strikes = [atm + step * i for i in range(-strikes_each_side, strikes_each_side + 1)]
    contracts = []
    for strike in strikes:
        strike_int = int(strike)
        contracts.append(
            {
                "strike": strike_int,
                "call_symbol": f"{underlying_symbol.upper()}{expiry_date.replace('-', '')}{strike_int}CE",
                "put_symbol": f"{underlying_symbol.upper()}{expiry_date.replace('-', '')}{strike_int}PE",
            }
        )
    return {
        "underlying_symbol": underlying_symbol.upper(),
        "expiry_date": expiry_date,
        "underlying_ltp": round(spot, 2),
        "strike_step": step,
        "contracts": contracts,
    }


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _black_scholes_greeks(
    spot: float,
    strike: float,
    days_to_expiry: float,
    iv: float = 0.25,
    rate: float = 0.07,
    option_type: str = "CE",
) -> dict[str, float]:
    t = max(days_to_expiry / 365.0, 1 / 365.0)
    if spot <= 0 or strike <= 0 or iv <= 0:
        raise ValueError("Invalid inputs for greeks calculation.")
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv**2) * t) / (iv * math.sqrt(t))
    d2 = d1 - iv * math.sqrt(t)
    is_call = option_type.upper() in {"CE", "CALL", "C"}
    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1
    gamma = math.exp(-0.5 * d1 * d1) / (spot * iv * math.sqrt(2 * math.pi * t))
    theta = -(spot * iv * math.exp(-0.5 * d1 * d1)) / (2 * math.sqrt(2 * math.pi * t))
    vega = spot * math.sqrt(t) * math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "iv": round(iv * 100, 2),
    }


def fetch_greeks(
    underlying: str,
    trading_symbol: str,
    expiry: str,
    exchange: str = "NSE",
    iv: float = 0.25,
) -> dict[str, Any]:
    spot = fetch_ltp(underlying, exchange)
    option_type = "CE" if trading_symbol.upper().endswith("CE") else "PE"
    digits = "".join(ch for ch in trading_symbol if ch.isdigit())
    strike = float(digits[-5:]) if len(digits) >= 5 else round(spot / 50) * 50
    expiry_dt = datetime.strptime(expiry[:10], "%Y-%m-%d").date()
    days = max((expiry_dt - date.today()).days, 1)
    greeks = _black_scholes_greeks(spot, strike, days, iv, option_type=option_type)
    return {
        "underlying": underlying.upper(),
        "trading_symbol": trading_symbol.upper(),
        "expiry": expiry,
        "spot": round(spot, 2),
        "strike": strike,
        "days_to_expiry": days,
        "greeks": greeks,
        "model": "black_scholes_estimate",
    }


def fetch_option_chain_summary(
    underlying: str,
    exchange: str = "NSE",
    expiry_date: str | None = None,
    strikes_each_side: int = 5,
) -> dict[str, Any]:
    """Return synthetic option chain when Groww API is unavailable."""
    quote = fetch_quote(underlying, exchange)
    spot = quote["last_price"]
    expiry = expiry_date or fetch_expiries(underlying, exchange)["expiries"][0]
    step = _strike_step(underlying, spot)
    atm = round(spot / step) * step
    strikes: dict[str, Any] = {}
    for i in range(-strikes_each_side, strikes_each_side + 1):
        strike = int(atm + step * i)
        expiry_dt = datetime.strptime(expiry[:10], "%Y-%m-%d").date()
        days = max((expiry_dt - date.today()).days, 1)
        ce = _black_scholes_greeks(spot, strike, days, option_type="CE")
        pe = _black_scholes_greeks(spot, strike, days, option_type="PE")
        strikes[str(strike)] = {
            "CE": {"ltp": None, "greeks": ce, "open_interest": None, "volume": None},
            "PE": {"ltp": None, "greeks": pe, "open_interest": None, "volume": None},
        }
    return {
        "underlying": underlying.upper(),
        "exchange": exchange.upper(),
        "expiry_date": expiry,
        "underlying_ltp": spot,
        "strikes": strikes,
        "note": "Synthetic chain from Yahoo spot + Black-Scholes estimates.",
        "quote": quote,
    }
