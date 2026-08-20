"""Groww MCP SSE gateway for Cursor mobile / Render.

Public URL to paste in Cursor: https://YOUR-SERVICE.onrender.com/sse
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from mcp.server import MCPServer as FastMCP

mcp = FastMCP(
    "groww-mcp",
    instructions="Groww portfolio, live prices, and order tools over SSE.",
)


def _mock() -> bool:
    return os.getenv("GROWW_MOCK_MODE", "1").lower() in {"1", "true", "yes"} or not (
        os.getenv("GROWW_ACCESS_TOKEN")
        or os.getenv("GROWW_CREDENTIALS")
        or (
            os.getenv("GROWW_API_KEY")
            and (
                os.getenv("TOTP_SECRET")
                or os.getenv("GROWW_TOTP_SECRET")
                or os.getenv("GROWW_API_SECRET")
                or os.getenv("GROWW_SECRET")
            )
        )
    )


@mcp.tool()
def groww_health_check() -> dict[str, Any]:
    """Verify the SSE MCP server is up."""
    return {"status": "ok", "transport": "sse", "sse": "/sse", "mock_mode": _mock()}


@mcp.tool()
def groww_get_holdings() -> dict[str, Any]:
    """Return Groww portfolio holdings."""
    if _mock():
        return {
            "mode": "mock",
            "holdings": [
                {"trading_symbol": "RELIANCE", "quantity": 10, "average_price": 2450.5},
                {"trading_symbol": "INFY", "quantity": 25, "average_price": 1520.0},
            ],
        }
    from groww_mcp.config import Settings
    from groww_mcp.groww_client import GrowwClient

    return GrowwClient(Settings.from_env()).get_holdings()


@mcp.tool()
def groww_get_ltp(trading_symbol: str, exchange: str = "NSE") -> dict[str, Any]:
    """Return last traded price (live tracking)."""
    if _mock():
        return {
            "mode": "mock",
            "trading_symbol": trading_symbol.upper(),
            "exchange": exchange.upper(),
            "ltp": 1234.56,
        }
    from groww_mcp.config import Settings
    from groww_mcp.groww_client import GrowwClient

    return GrowwClient(Settings.from_env()).get_ltp(trading_symbol, exchange)


@mcp.tool()
def groww_get_portfolio() -> dict[str, Any]:
    """Return full portfolio with live market prices, invested value, current value, and P&L."""
    if _mock():
        client_ltp = 1234.56
        holdings = [
            {"trading_symbol": "RELIANCE", "quantity": 10, "average_price": 2450.5},
            {"trading_symbol": "INFY", "quantity": 25, "average_price": 1520.0},
        ]
        rows = []
        total_invested = 0.0
        total_current = 0.0
        for h in holdings:
            invested = h["quantity"] * h["average_price"]
            current = h["quantity"] * client_ltp
            total_invested += invested
            total_current += current
            rows.append(
                {
                    "trading_symbol": h["trading_symbol"],
                    "quantity": h["quantity"],
                    "average_price": h["average_price"],
                    "ltp": client_ltp,
                    "invested": round(invested, 2),
                    "current_value": round(current, 2),
                    "pnl": round(current - invested, 2),
                    "pnl_percent": round(((current - invested) / invested) * 100, 2),
                    "price_source": "mock",
                }
            )
        total_pnl = total_current - total_invested
        return {
            "mode": "mock",
            "price_source": ["mock"],
            "holdings": rows,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / total_invested) * 100, 2),
        }

    from groww_mcp.config import Settings
    from groww_mcp.groww_client import GrowwClient

    return GrowwClient(Settings.from_env()).get_portfolio_summary()


@mcp.tool()
def groww_place_order(
    trading_symbol: str,
    quantity: int,
    transaction_type: str = "BUY",
    order_type: str = "MARKET",
    exchange: str = "NSE",
    product: str = "CNC",
    price: float = 0.0,
) -> dict[str, Any]:
    """Place a Groww order (mock unless live credentials are set)."""
    if _mock():
        return {
            "mode": "mock",
            "status": "NEW",
            "groww_order_id": "MOCK-ORDER-1",
            "trading_symbol": trading_symbol.upper(),
            "quantity": quantity,
            "transaction_type": transaction_type.upper(),
            "order_type": order_type.upper(),
            "exchange": exchange.upper(),
            "product": product.upper(),
            "price": price,
        }
    from growwapi import GrowwAPI

    from groww_mcp.config import Settings
    from groww_mcp.groww_client import GrowwClient

    client = GrowwClient(Settings.from_env())._ensure_client()
    return client.place_order(
        validity=GrowwAPI.VALIDITY_DAY,
        exchange=exchange.upper(),
        order_type=order_type.upper(),
        product=product.upper(),
        quantity=quantity,
        segment=GrowwAPI.SEGMENT_CASH,
        trading_symbol=trading_symbol.upper(),
        transaction_type=transaction_type.upper(),
        price=price or None,
    )


sse_app = mcp.sse_app(host="0.0.0.0", sse_path="/sse", message_path="/messages/")
app = FastAPI(title="Groww MCP SSE", version="1.0.0")


@app.get("/")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "sse": "/sse"}


for _route in sse_app.router.routes:
    app.router.routes.append(_route)
