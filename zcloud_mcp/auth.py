"""
Authentication utilities for Zededa MCP tools.
"""
from fastmcp.server.dependencies import get_http_headers
from utils import logger


async def ensure_bearer_token() -> str | None:
    """Return the Bearer token from the request headers, or None if absent/invalid."""
    headers = get_http_headers(include_all=True)
    auth_header = headers.get("x-zedcloud-authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.error("Authorization header is missing or not a Bearer token.")
        return None
    return auth_header
