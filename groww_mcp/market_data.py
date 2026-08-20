from __future__ import annotations


def fetch_ltp(trading_symbol: str, exchange: str = "NSE") -> float:
  """Fetch LTP from Yahoo Finance when Groww market-data APIs are unavailable."""
  import yfinance as yf

  symbol = trading_symbol.upper()
  suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
  ticker = yf.Ticker(f"{symbol}{suffix}")
  info = ticker.fast_info
  ltp = info.get("last_price") or info.get("lastPrice")
  if ltp:
    return float(ltp)

  hist = ticker.history(period="1d")
  if hist.empty:
    raise ValueError(f"No market data found for {symbol} on {exchange}.")
  return float(hist["Close"].iloc[-1])
