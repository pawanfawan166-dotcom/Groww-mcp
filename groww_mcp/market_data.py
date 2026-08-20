from __future__ import annotations

from typing import Any


def _yahoo_symbol(trading_symbol: str, exchange: str = "NSE") -> str:
    sym = trading_symbol.upper()
    index_map = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    }
    if sym in index_map:
        return index_map[sym]
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return f"{sym}{suffix}"


def _ticker(trading_symbol: str, exchange: str = "NSE"):
    import yfinance as yf

    return yf.Ticker(_yahoo_symbol(trading_symbol, exchange))


def fetch_ltp(trading_symbol: str, exchange: str = "NSE") -> float:
    """Fetch LTP from Yahoo Finance when Groww market-data APIs are unavailable."""
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

    prev_close = float(info.get("previous_close") or info.get("previousClose") or 0)
    if not prev_close and len(hist) > 1:
        prev_close = float(hist["Close"].iloc[-2])

    day_change = float(last_price) - prev_close if prev_close else 0.0
    day_change_perc = (day_change / prev_close * 100) if prev_close else 0.0

    ohlc = {}
    if not hist.empty:
        today = hist.iloc[-1]
        ohlc = {
            "open": float(today["Open"]),
            "high": float(today["High"]),
            "low": float(today["Low"]),
            "close": float(today["Close"]),
        }

    return {
        "last_price": float(last_price),
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
    return {
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
    }


def fetch_option_chain_summary(
    underlying: str,
    exchange: str = "NSE",
    expiry_date: str | None = None,
) -> dict[str, Any]:
    """Return underlying snapshot when Groww option-chain API is unavailable."""
    quote = fetch_quote(underlying, exchange)
    return {
        "underlying": underlying.upper(),
        "exchange": exchange.upper(),
        "expiry_date": expiry_date,
        "underlying_ltp": quote["last_price"],
        "note": "Full strike-wise option chain requires Groww live-data permission.",
        "quote": quote,
    }
