"""Groww MCP SSE gateway for Cursor mobile / Render.

Public URL to paste in Cursor: https://YOUR-SERVICE.onrender.com/sse
"""

from __future__ import annotations

from fastapi import FastAPI
from mcp.server import MCPServer as FastMCP

from groww_mcp.all_tools import ALL_TOOLS

mcp = FastMCP(
    "groww-mcp",
    instructions="Groww portfolio, live prices, orders, smart orders, and market data over SSE (31 tools).",
)

for _tool in ALL_TOOLS:
    mcp.tool()(_tool)

sse_app = mcp.sse_app(host="0.0.0.0", sse_path="/sse", message_path="/messages/")
app = FastAPI(title="Groww MCP SSE", version="2.0.0")


@app.get("/")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "sse": "/sse", "tools": "31"}


for _route in sse_app.router.routes:
    app.router.routes.append(_route)
