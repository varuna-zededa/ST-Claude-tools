"""
Zededa MCP tools for app profile management.

These tools provide agents with a comprehensive interface for querying and
managing app profiles from Zedcloud. App profiles define application configurations
and settings that can be deployed to edge nodes.

Note: App profiles are NOT related to project policies.

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


def register_app_profile_tools(mcp):
    """Register all app profile-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] App profile tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"app_profiles", "all_app_profiles"})
    async def get_app_profiles(
        summary: Optional[bool] = None,
        name_pattern: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
        fields: Optional[list[str]] = None,
    ) -> dict[str, Any] | str:
        """
        Query app profiles from Zedcloud with comprehensive filtering options.

        This tool provides filtering and pagination options to query app profiles
        from the ZedCloud platform. App profiles define application configurations
        and settings that can be deployed to edge nodes.

        Note: This is NOT for project policies. Use this tool specifically for
        application profile configurations.

        Args:
            summary: Return summary information only (boolean)
            name_pattern: Filter by profile name pattern (supports wildcards)
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            fields: Specific fields to return (valid: id, name, title, description)

        Returns:
            Dictionary containing list of app profiles with pagination info.
            Returns error message if request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "app-profiles-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["filter.namePattern"] = name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))  # Cap at 50
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if fields:
            valid_fields = ["id", "name", "title", "description"]
            for field in fields:
                if field in valid_fields:
                    params.setdefault("fields", []).append(field)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/appprofiles"
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
            return "Failed to retrieve app profiles."
        return response

    @mcp.tool(tags={"app_profile", "lookup_by_id_or_name"})
    async def get_app_profile(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific app profile.

        Use this tool when you need to get complete configuration and metadata for an app profile.
        The tool automatically resolves the profile from either its unique ID or human-readable name.

        Note: This is NOT for project policies. Use this tool specifically for
        application profile configurations.

        Args:
            identifier: The profile ID or name to look up
            lookup_by: Search method - "id" for profile ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing app profile details including ID, name, configuration, and version info.
            Returns error message if profile not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("app-profiles-detail.json")
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
        url = f"{ZEDEDA_API_BASE}/api/v1/appprofiles/{lookup_endpoint}/{identifier_encoded}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"App profile not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"app_profile", "versions", "lookup_by_id_or_name"})
    async def get_app_profile_versions(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name",
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
    ) -> dict[str, Any] | str:
        """
        Query app profile versions by app profile ID or name.

        This tool retrieves all available versions of a specific app profile,
        useful for tracking configuration changes and rollback options.

        Args:
            identifier: The profile ID or name to look up versions for
            lookup_by: Search method - "id" for profile ID lookup or "name" for name lookup (default: "name")
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch

        Returns:
            Dictionary containing list of app profile versions with pagination info.
            Returns error message if profile not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("app-profiles-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return "Error: identifier parameter is required and cannot be empty"

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

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        identifier_encoded = (
            identifier if lookup_by == "id" else urllib.parse.quote(identifier)
        )
        url = f"{ZEDEDA_API_BASE}/api/v1/appprofiles/{lookup_endpoint}/{identifier_encoded}/version"
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
            return f"App profile versions not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
