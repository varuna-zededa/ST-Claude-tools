"""
Third Party Plugins for Orchestrator Service.

This module provides MCP tools for managing third party plugins
in ZedCloud. Third party plugins allow integration with external
services and systems for extended functionality.

Design Principles:
- All list operations support pagination via next_page_token
- Single resource lookups support both ID and name-based queries
- Consistent error messages following the pattern:
    "Failed to retrieve {resource}." or "No {resource} found with {field}."
- Mock data support via USE_MOCK_API_MCP_DATA for testing
"""

import logging
from typing import Any, Literal, Optional
import urllib.parse
from utils import (
    make_zededa_request,
    ZEDEDA_API_BASE,
    load_mock_json,
)
from auth import ensure_bearer_token

logger = logging.getLogger(__name__)

def register_third_party_plugin_tools(mcp):
    """Register all third party plugin-related MCP tools (GET methods only)."""
    logger.info("Registering third party plugin tools with MCP server")
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"plugins", "third_party", "get_all_plugins",
                    "integrations"})
    async def get_plugins(
            summary: Optional[bool] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            name_pattern: Optional[str] = None,
            integration_type: Optional[int] = None) -> dict[str, Any] | str:
        """
        Query third party plugins from ZedCloud.

        Retrieves a list of third party plugins with comprehensive filtering
        options. These plugins enable integration with external services.

        Args:
            summary: Return summary information only.
            page_token: Token for pagination to get next page of results.
            page_num: Page number for pagination (default: 1).
            page_size: Number of results per page (default: 20, max: 50).
            total_pages: Total number of pages to retrieve.
            name_pattern: Filter plugins by name pattern.
            integration_type: Filter by integration type.

        Returns:
            dict: List of third party plugins matching the query criteria.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("third-party-plugins-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for third party plugins list not found.")
                return "Mock data for third party plugins list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if name_pattern:
            params["namePattern"] = name_pattern
        if integration_type is not None:
            params["integrationType"] = str(integration_type)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/plugins"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(
                            f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(
                        f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve third party plugins."

        return response

    @mcp.tool(tags={"plugins", "third_party", "get_plugin", "integration", "by_id", "by_name"})
    async def get_plugin(
            identifier: str,
            lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """
        Get a specific third party plugin from ZedCloud.

        Retrieves detailed information about a single third party plugin
        by its ID or name.

        Args:
            identifier: The ID or name of the plugin to retrieve.
            lookup_by: Whether to look up by "id" or "name" (default: "name").

        Returns:
            dict: Detailed plugin configuration data.
            str: Error message if the plugin is not found or request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("third-party-plugins-detail.json")
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for third party plugin detail not found.")
                return "Mock data for third party plugin detail not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/plugins/id/{identifier}"
        else:
            url = (f"{ZEDEDA_API_BASE}/api/v1/plugins/name/"
                   f"{urllib.parse.quote(identifier)}")

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"No plugin found with {lookup_by}: {identifier}."
        return response
