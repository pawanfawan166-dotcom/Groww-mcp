from __future__ import annotations

from typing import Any

from groww_mcp.extended_client import ExtendedGrowwClient
from groww_mcp.config import Settings
from groww_mcp.runtime import is_mock


def _c() -> ExtendedGrowwClient:
    return ExtendedGrowwClient(Settings.from_env())


# 1
def groww_get_user_profile() -> dict[str, Any]:
    """Return Groww user profile."""
    if is_mock():
        return {"mode": "mock", "data": {"name": "Demo User"}}
    return _c().get_user_profile()


# 2
def groww_get_holdings() -> dict[str, Any]:
    """Return Groww portfolio holdings."""
    if is_mock():
        return {"mode": "mock", "holdings": [{"trading_symbol": "RELIANCE", "quantity": 10, "average_price": 2450.5}]}
    return _c().get_holdings()


# 3
def groww_get_positions(segment: str | None = None) -> dict[str, Any]:
    """Return all open positions, optionally filtered by segment (CASH, FNO, COMMODITY)."""
    if is_mock():
        return {"mode": "mock", "data": {"positions": []}}
    return _c().get_positions(segment)


# 4
def groww_get_position_by_symbol(trading_symbol: str, segment: str = "CASH") -> dict[str, Any]:
    """Return position for a specific trading symbol."""
    if is_mock():
        return {"mode": "mock", "data": {"positions": []}}
    return _c().get_position_by_symbol(trading_symbol, segment)


# 5
def groww_get_margin() -> dict[str, Any]:
    """Return available margin and cash balances."""
    if is_mock():
        return {"mode": "mock", "data": {"clear_cash": 100000}}
    return _c().get_margin()


# 6
def groww_get_portfolio() -> dict[str, Any]:
    """Return full portfolio with live prices, invested value, current value, and P&L."""
    if is_mock():
        return {"mode": "mock", "holdings": [], "total_invested": 0, "total_current_value": 0, "total_pnl": 0}
    return _c().get_portfolio_summary()


# 7
def groww_get_order_list(segment: str | None = None, page: int = 0, page_size: int = 25) -> dict[str, Any]:
    """Return order list with optional segment filter."""
    if is_mock():
        return {"mode": "mock", "data": {"order_list": []}}
    return _c().get_orders(segment, page, page_size)


# 8
def groww_get_order_detail(groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    """Return detailed information for one order."""
    if is_mock():
        return {"mode": "mock", "data": {"groww_order_id": groww_order_id}}
    return _c().get_order_detail(groww_order_id, segment)


# 9
def groww_get_order_status(groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    """Return status for one order."""
    if is_mock():
        return {"mode": "mock", "data": {"order_status": "NEW"}}
    return _c().get_order_status(groww_order_id, segment)


# 10
def groww_get_order_status_by_reference(order_reference_id: str, segment: str = "CASH") -> dict[str, Any]:
    """Return order status by reference ID."""
    if is_mock():
        return {"mode": "mock", "data": {"order_status": "NEW"}}
    return _c().get_order_status_by_reference(order_reference_id, segment)


# 11
def groww_get_order_trades(groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    """Return trade executions for an order."""
    if is_mock():
        return {"mode": "mock", "data": {"trades": []}}
    return _c().get_order_trades(groww_order_id, segment)


# 12
def groww_place_order(
    trading_symbol: str,
    quantity: int,
    transaction_type: str = "BUY",
    order_type: str = "MARKET",
    exchange: str = "NSE",
    product: str = "CNC",
    segment: str = "CASH",
    price: float = 0.0,
) -> dict[str, Any]:
    """Place a Groww order."""
    if is_mock():
        return {"mode": "mock", "groww_order_id": "MOCK-ORDER-1", "trading_symbol": trading_symbol.upper()}
    return _c().place_order_full(
        trading_symbol, quantity, transaction_type, order_type, exchange, product, segment, price
    )


# 13
def groww_modify_order(
    groww_order_id: str,
    quantity: int,
    order_type: str = "LIMIT",
    segment: str = "CASH",
    price: float | None = None,
) -> dict[str, Any]:
    """Modify an existing open order."""
    if is_mock():
        return {"mode": "mock", "groww_order_id": groww_order_id, "status": "MODIFIED"}
    return _c().modify_order(groww_order_id, quantity, order_type, segment, price)


# 14
def groww_cancel_order(groww_order_id: str, segment: str = "CASH") -> dict[str, Any]:
    """Cancel an open order."""
    if is_mock():
        return {"mode": "mock", "groww_order_id": groww_order_id, "status": "CANCELLED"}
    return _c().cancel_order(groww_order_id, segment)


# 15
def groww_get_ltp(trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
    """Return last traded price for one or comma-separated symbols."""
    if is_mock():
        return {"mode": "mock", "ltp": 1234.56, "trading_symbol": trading_symbol.upper()}
    return _c().get_ltp(trading_symbol, exchange, segment)


# 16
def groww_get_quote(trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
    """Return live quote with day change, volume, and OHLC snapshot."""
    if is_mock():
        return {"mode": "mock", "quote": {"last_price": 1234.56}}
    return _c().get_quote(trading_symbol, exchange, segment)


# 17
def groww_get_ohlc(trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
    """Return OHLC for one or comma-separated symbols."""
    if is_mock():
        return {"mode": "mock", "ohlc": {"open": 1200, "high": 1250, "low": 1190, "close": 1234.56}}
    return _c().get_ohlc(trading_symbol, exchange, segment)


# 18
def groww_get_option_chain(underlying: str, expiry_date: str, exchange: str = "NSE") -> dict[str, Any]:
    """Return option chain for underlying and expiry (YYYY-MM-DD)."""
    if is_mock():
        return {"mode": "mock", "option_chain": {"underlying_ltp": 25000}}
    return _c().get_option_chain(underlying, expiry_date, exchange)


# 19
def groww_get_greeks(
    exchange: str,
    underlying: str,
    trading_symbol: str,
    expiry: str,
) -> dict[str, Any]:
    """Return option Greeks for a contract."""
    if is_mock():
        return {"mode": "mock", "data": {"greeks": {"delta": 0.5}}}
    return _c().get_greeks(exchange, underlying, trading_symbol, expiry)


# 20
def groww_get_historical_candles(
    exchange: str,
    segment: str,
    groww_symbol: str,
    start_time: str,
    end_time: str,
    candle_interval: str = "1day",
) -> dict[str, Any]:
    """Return historical candle data between start_time and end_time."""
    if is_mock():
        return {"mode": "mock", "data": {"candles": []}}
    return _c().get_historical_candles(exchange, segment, groww_symbol, start_time, end_time, candle_interval)


# 21
def groww_get_expiries(
    exchange: str,
    underlying_symbol: str,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Return F&O expiry dates for an underlying."""
    if is_mock():
        return {"mode": "mock", "data": {"expiries": ["2025-08-28"]}}
    return _c().get_expiries(exchange, underlying_symbol, year, month)


# 22
def groww_get_contracts(exchange: str, underlying_symbol: str, expiry_date: str) -> dict[str, Any]:
    """Return F&O contracts for underlying and expiry."""
    if is_mock():
        return {"mode": "mock", "data": {"contracts": []}}
    return _c().get_contracts(exchange, underlying_symbol, expiry_date)


# 23
def groww_get_smart_orders(segment: str | None = None) -> dict[str, Any]:
    """Return GTT/OCO smart orders."""
    if is_mock():
        return {"mode": "mock", "data": {"smart_orders": []}}
    return _c().get_smart_orders(segment)


# 24
def groww_get_smart_order(smart_order_id: str, segment: str = "CASH", smart_order_type: str = "GTT") -> dict[str, Any]:
    """Return one smart order by ID."""
    if is_mock():
        return {"mode": "mock", "data": {"smart_order_id": smart_order_id}}
    return _c().get_smart_order(smart_order_id, segment, smart_order_type)


# 25
def groww_create_smart_order_gtt(
    trading_symbol: str,
    quantity: int,
    trigger_price: str,
    trigger_direction: str,
    transaction_type: str,
    exchange: str = "NSE",
    product_type: str = "CNC",
    segment: str = "CASH",
    order_type: str = "MARKET",
    price: str | None = None,
    duration: str = "DAY",
) -> dict[str, Any]:
    """Create a GTT smart order."""
    if is_mock():
        return {"mode": "mock", "smart_order_id": "MOCK-GTT-1"}
    return _c().create_smart_order_gtt(
        trading_symbol, quantity, trigger_price, trigger_direction, transaction_type,
        exchange, product_type, segment, order_type, price, duration,
    )


# 26
def groww_modify_smart_order(
    smart_order_id: str,
    smart_order_type: str = "GTT",
    segment: str = "CASH",
    quantity: int | None = None,
    trigger_price: str | None = None,
) -> dict[str, Any]:
    """Modify a smart order."""
    if is_mock():
        return {"mode": "mock", "smart_order_id": smart_order_id}
    return _c().modify_smart_order(smart_order_id, smart_order_type, segment, quantity, trigger_price)


# 27
def groww_cancel_smart_order(
    smart_order_id: str,
    smart_order_type: str = "GTT",
    segment: str = "CASH",
) -> dict[str, Any]:
    """Cancel a smart order."""
    if is_mock():
        return {"mode": "mock", "smart_order_id": smart_order_id, "status": "CANCELLED"}
    return _c().cancel_smart_order(smart_order_id, smart_order_type, segment)


# 28
def groww_search_instrument(exchange: str, trading_symbol: str) -> dict[str, Any]:
    """Search instrument details by exchange and trading symbol."""
    if is_mock():
        return {"mode": "mock", "data": {"trading_symbol": trading_symbol.upper()}}
    return _c().search_instrument(exchange, trading_symbol)


# 29
def groww_get_instrument_by_groww_symbol(groww_symbol: str) -> dict[str, Any]:
    """Get instrument details by Groww symbol."""
    if is_mock():
        return {"mode": "mock", "data": {"groww_symbol": groww_symbol.upper()}}
    return _c().get_instrument_by_groww_symbol(groww_symbol)


# 30
def groww_calculate_order_margin(
    segment: str,
    trading_symbol: str,
    quantity: int,
    transaction_type: str,
    product: str = "CNC",
    order_type: str = "MARKET",
    exchange: str = "NSE",
    price: float = 0.0,
) -> dict[str, Any]:
    """Calculate margin required for an order."""
    if is_mock():
        return {"mode": "mock", "data": {"margin_required": 5000}}
    return _c().calculate_order_margin(segment, trading_symbol, quantity, transaction_type, product, order_type, exchange, price)


# 31
def groww_health_check() -> dict[str, Any]:
    """Verify the SSE MCP server is up."""
    return {"status": "ok", "transport": "sse", "sse": "/sse", "mock_mode": is_mock(), "tools": 31}


ALL_TOOLS = [
    groww_health_check,
    groww_get_user_profile,
    groww_get_holdings,
    groww_get_positions,
    groww_get_position_by_symbol,
    groww_get_margin,
    groww_get_portfolio,
    groww_get_order_list,
    groww_get_order_detail,
    groww_get_order_status,
    groww_get_order_status_by_reference,
    groww_get_order_trades,
    groww_place_order,
    groww_modify_order,
    groww_cancel_order,
    groww_get_ltp,
    groww_get_quote,
    groww_get_ohlc,
    groww_get_option_chain,
    groww_get_greeks,
    groww_get_historical_candles,
    groww_get_expiries,
    groww_get_contracts,
    groww_get_smart_orders,
    groww_get_smart_order,
    groww_create_smart_order_gtt,
    groww_modify_smart_order,
    groww_cancel_smart_order,
    groww_search_instrument,
    groww_get_instrument_by_groww_symbol,
    groww_calculate_order_margin,
]
