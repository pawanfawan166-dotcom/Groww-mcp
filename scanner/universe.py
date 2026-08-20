"""NSE F&O universe loader."""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

FO_CSV_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50", "SENSEX"}

SECTOR_MAP: dict[str, str] = {
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "BPCL": "Energy",
    "IOC": "Energy",
    "HINDPETRO": "Energy",
    "GAIL": "Energy",
    "COALINDIA": "Energy",
    "TATAPOWER": "Power",
    "NTPC": "Power",
    "POWERGRID": "Power",
    "ADANIGREEN": "Power",
    "ADANIPORTS": "Infrastructure",
    "ADANIENT": "Conglomerate",
    "LT": "Infrastructure",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "INDUSINDBK": "Banking",
    "BANKBARODA": "Banking",
    "PNB": "Banking",
    "CANBK": "Banking",
    "IDFCFIRSTB": "Banking",
    "FEDERALBNK": "Banking",
    "AUBANK": "Banking",
    "BANDHANBNK": "Banking",
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "HCLTECH": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "COFORGE": "IT",
    "MPHASIS": "IT",
    "PERSISTENT": "IT",
    "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals",
    "HINDALCO": "Metals",
    "VEDL": "Metals",
    "SAIL": "Metals",
    "NMDC": "Metals",
    "JINDALSTEL": "Metals",
    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "DIVISLAB": "Pharma",
    "LUPIN": "Pharma",
    "AUROPHARMA": "Pharma",
    "GLENMARK": "Pharma",
    "TITAN": "Consumer",
    "HINDUNILVR": "Consumer",
    "ITC": "Consumer",
    "NESTLEIND": "Consumer",
    "BRITANNIA": "Consumer",
    "DABUR": "Consumer",
    "MARICO": "Consumer",
    "TATAMOTORS": "Auto",
    "M&M": "Auto",
    "MARUTI": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",
    "BAJAJ-AUTO": "Auto",
    "TVSMOTOR": "Auto",
    "ASHOKLEY": "Auto",
    "BAJFINANCE": "NBFC",
    "BAJAJFINSV": "NBFC",
    "HDFCLIFE": "Insurance",
    "ICICIPRULI": "Insurance",
    "SBILIFE": "Insurance",
    "MCX": "Financial Services",
    "MUTHOOTFIN": "NBFC",
    "CHOLAFIN": "NBFC",
    "SHRIRAMFIN": "NBFC",
    "PREMIERENE": "Renewable Energy",
}


def _parse_fo_csv(text: str) -> list[str]:
    symbols: list[str] = []
    reader = csv.reader(text.splitlines())
    next(reader, None)
    for row in reader:
        if len(row) < 2:
            continue
        symbol = row[1].strip().upper()
        if not symbol or symbol in INDEX_SYMBOLS or symbol in {"SYMBOL", "NIFTYFPI"}:
            continue
        if re.fullmatch(r"[A-Z0-9&-]+", symbol):
            symbols.append(symbol)
    return sorted(set(symbols))


@lru_cache(maxsize=1)
def load_fno_symbols(cache_path: str | None = None) -> list[str]:
    """Return equity symbols in the NSE F&O universe."""
    local = Path(cache_path) if cache_path else Path(__file__).resolve().parent / "data" / "fo_symbols.txt"
    if local.exists():
        return [line.strip() for line in local.read_text().splitlines() if line.strip()]

    request = Request(FO_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")
    symbols = _parse_fo_csv(text)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("\n".join(symbols))
    return symbols


def yfinance_symbol(nse_symbol: str) -> str:
    return f"{nse_symbol}.NS"


def sector_for(symbol: str) -> str:
    return SECTOR_MAP.get(symbol.upper(), "Other")
