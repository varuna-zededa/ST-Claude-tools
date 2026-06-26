"""
Zededa MCP tools for profile deployment management.

These tools provide agents with a comprehensive interface for querying and
managing profile deployments from Zedcloud. Profile deployments track the
deployment status and configuration of app profiles to edge nodes.

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


def register_profile_deployment_tools(mcp):
    """Register all profile deployment-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Profile deployment tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"profile_deployments", "all_profile_deployments"})
    async def get_all_profile_deployments(
        profile_deployment_id: Optional[str] = None,
        name_pattern: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
    ) -> dict[str, Any] | str:
        """
        Query profile deployments from Zedcloud with comprehensive filtering options.

        This tool provides filtering and pagination options to query profile deployments
        from the ZedCloud platform. Profile deployments track the deployment status
        and configuration of app profiles to edge nodes.

        Args:
            profile_deployment_id: Filter by specific profile deployment ID
            name_pattern: Filter by deployment name pattern (supports wildcards)
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch

        Returns:
            Dictionary containing list of profile deployments with pagination info.
            Returns error message if request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "profile-deployments-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if profile_deployment_id:
            params["filter.profileDeploymentId"] = profile_deployment_id
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

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/profiledeployments"
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
            return "Failed to retrieve profile deployments."

        return response

    @mcp.tool(tags={"profile_deployment", "lookup_by_id_or_name"})
    async def get_profile_deployment(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific profile deployment.

        Use this tool when you need to get complete configuration and status for a profile deployment.
        The tool automatically resolves the deployment from either its unique ID or human-readable name.

        Args:
            identifier: The deployment ID or name to look up
            lookup_by: Search method - "id" for deployment ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing profile deployment details including ID, name, status, and target nodes.
            Returns error message if deployment not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("profile-deployments-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        identifier_encoded = (
            identifier if lookup_by == "id" else urllib.parse.quote(identifier)
        )
        url = f"{ZEDEDA_API_BASE}/api/v1/profiledeployments/{lookup_endpoint}/{identifier_encoded}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Profile deployment not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(
        tags={"profile_deployment", "resource_status", "monitoring", "edge_nodes"}
    )
    async def get_profile_deployment_resource_status(
        deployment_id: str,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
    ) -> dict[str, Any] | str:
        """
        Query profile deployment resource status by deployment ID.

        This tool retrieves the resource status for all nodes targeted by a specific
        profile deployment, useful for monitoring deployment progress and health.

        Args:
            deployment_id: The profile deployment ID to query resource status for
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch

        Returns:
            Dictionary containing resource status for nodes in the deployment.
            Returns error message if deployment not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "profile-deployments-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                return mock

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

        url = f"{ZEDEDA_API_BASE}/api/v1/profiledeployments/id/{deployment_id}/resourcestatus"
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
            return (
                f"Resource status not found for profile deployment ID: {deployment_id}."
            )
        return response
