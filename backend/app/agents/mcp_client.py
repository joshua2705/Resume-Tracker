"""Gmail MCP connection.

Wraps the Gmail MCP server (default: @gongrzhe/server-gmail-autoauth-mcp, run
over stdio via npx) as LangChain tools using langchain-mcp-adapters. The gmail
agent uses these tools; nothing else in the app talks to the MCP directly.

The command/args are configurable (see config.py / .env) so you can point at a
different Gmail MCP. Tools are loaded on demand and the client is closed after
each scan — daily cadence means a long-lived connection isn't worth it.
"""
from __future__ import annotations

from ..config import get_settings


def _server_config() -> dict:
    s = get_settings()
    return {
        "gmail": {
            "command": s.gmail_mcp_command,
            "args": s.gmail_mcp_args,
            "transport": "stdio",
        }
    }


async def load_gmail_tools() -> list:
    """Return the Gmail MCP tools as LangChain tools. Raises if the MCP or the
    adapter package is unavailable — the caller decides how to handle it."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(_server_config())
    # get_tools() establishes the stdio session and lists the server's tools.
    return await client.get_tools()
