"""
DataStream Configs for Orchestrator Service.

This module provides MCP tools for managing datastreams (data stream
configurations) in ZedCloud. Datastreams define how data flows from
edge devices to cloud services for monitoring and analytics.

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


def register_datastream_tools(mcp):
    """Register all datastream-related MCP tools (GET methods only)."""
    logger.info("Registering datastream tools with MCP server")
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"datastreams", "all_datastreams"})
    async def get_datastreams(
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            name_pattern: Optional[str] = None,
            type: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query datastream configs from ZedCloud Orchestrator Service.

        Retrieves a list of datastream configurations with comprehensive
        filtering options. Datastreams define how data flows from edge
        devices to cloud services.

        Args:
            page_token: Token for pagination to get next page of results.
            page_num: Page number for pagination (default: 1).
            page_size: Number of results per page (default: 20, max: 50).
            total_pages: Total number of pages to retrieve.
            name_pattern: Filter datastreams by name pattern.
            type: Filter by datastream type.

        Returns:
            dict: List of datastream configs matching the query criteria.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("datastreams-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for datastreams list not found.")
                return "Mock data for datastreams list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

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
        if type:
            params["type"] = type

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/datastreams"
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
            return "Failed to retrieve datastream configs."

        return response

    @mcp.tool(tags={"datastreams", "lookup_by_id_or_name"})
    async def get_datastream(
            identifier: str,
            lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """
        Get a specific datastream config from ZedCloud.

        Retrieves detailed information about a single datastream configuration
        by its ID or name.

        Args:
            identifier: The ID or name of the datastream to retrieve.
            lookup_by: Whether to look up by "id" or "name" (default: "name").

        Returns:
            dict: Detailed datastream configuration data.
            str: Error message if the datastream is not found or request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("datastreams-detail.json")
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for datastreams detail not found.")
                return "Mock data for datastreams detail not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/datastreams/id/{identifier}"
        else:
            url = (f"{ZEDEDA_API_BASE}/api/v1/datastreams/name/"
                   f"{urllib.parse.quote(identifier)}")

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"No datastream found with {lookup_by}: {identifier}."
        return response
