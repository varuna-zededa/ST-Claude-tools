"""
Zededa MCP tools for asset group management.

These tools provide agents with a comprehensive interface for querying and
managing asset groups from Zedcloud. Asset groups are logical groupings of
edge nodes that allow for organized management and policy application.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import urllib.parse
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, logger
from auth import ensure_bearer_token


def register_asset_group_tools(mcp):
    """Register all asset group-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Asset group tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"asset_groups", "all_asset_groups"})
    async def get_asset_groups(
        project_name_pattern: Optional[str] = None,
        name_pattern: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
        summary: Optional[bool] = None,
    ) -> dict[str, Any] | str:
        """
        Query asset groups from Zedcloud with comprehensive filtering options.

        This tool provides filtering and pagination options to query asset groups
        from the ZedCloud platform. Asset groups are logical groupings of edge nodes
        that allow for organized management and policy application.

        Args:
            project_name_pattern: Filter by project name pattern (supports wildcards)
            name_pattern: Filter by asset group name pattern (supports wildcards)
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            summary: Return summary information only (boolean)

        Returns:
            Dictionary containing list of asset groups with pagination info.
            Returns error message if request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "asset-groups-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if name_pattern:
            params["namePattern"] = name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))  # Cap at 50
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if summary is not None:
            params["summary"] = str(summary).lower()

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/assetgroups"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve asset groups."

        return response

    @mcp.tool(tags={"asset_group", "lookup_by_id_or_name"})
    async def get_asset_group(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific asset group.

        Use this tool when you need to get complete configuration and membership for an asset group.
        The tool automatically resolves the group from either its unique ID or human-readable name.

        Args:
            identifier: The asset group ID or name to look up
            lookup_by: Search method - "id" for group ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing asset group details including ID, name, member nodes, and policies.
            Returns error message if asset group not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("asset-groups-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return "Error: identifier parameter is required and cannot be empty"

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        identifier_encoded = (
            identifier if lookup_by == "id" else urllib.parse.quote(identifier)
        )
        url = f"{ZEDEDA_API_BASE}/api/v1/assetgroups/{lookup_endpoint}/{identifier_encoded}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Asset group not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
