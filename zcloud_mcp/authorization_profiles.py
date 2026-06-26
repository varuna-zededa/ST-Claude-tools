"""
Authorization Profiles (AAA) Management.

This module provides MCP tools for managing authorization profiles
(AAA profiles) in ZedCloud. Authorization profiles define access
control and authentication settings for users and services.

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


def register_auth_profiles_tools(mcp):
    """Register all Authorization profiles-related MCP tools (GET methods only)."""
    logger.info("Registering authorization profiles tools with MCP server")
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"get_all_auth_profiles", "iam", "authorization", "auth_profiles",
                    "access_control"})
    async def get_auth_profiles(
            summary: Optional[bool] = None,
            sfdc_id: Optional[str] = None,
            hubspot_id: Optional[str] = None,
            project: Optional[str] = None,
            name_pattern: Optional[str] = None,
            all: Optional[bool] = None,
            role_name: Optional[str] = None,
            size: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """
        Query AAA (Authorization) profiles from ZedCloud.

        Retrieves a list of authorization profiles with comprehensive
        filtering options. Authorization profiles define access control
        and authentication settings.

        Args:
            summary: Return summary information only.
            sfdc_id: Filter by Salesforce ID.
            hubspot_id: Filter by HubSpot ID.
            project: Filter by project name.
            name_pattern: Filter profiles by name pattern.
            all: Include all profiles.
            role_name: Filter by role name.
            size: Filter by size.
            page_token: Token for pagination to get next page of results.
            page_num: Page number for pagination (default: 1).
            page_size: Number of results per page (default: 20, max: 50).
            total_pages: Total number of pages to retrieve.

        Returns:
            dict: List of authorization profiles matching the query criteria.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("authorization-profiles-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for authorization profiles list not found.")
                return "Mock data for authorization profiles list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if sfdc_id:
            params["SfdcId"] = sfdc_id
        if hubspot_id:
            params["HubspotId"] = hubspot_id
        if project:
            params["project"] = project
        if name_pattern:
            params["namePattern"] = name_pattern
        if all is not None:
            params["all"] = str(all).lower()
        if role_name:
            params["roleName"] = role_name
        if size:
            params["size"] = size
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/authorization/profiles"
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
            return "Failed to retrieve AAA profiles."

        return response

    @mcp.tool(tags={"auth_profiles", "lookup_by_id_or_name", "iam", "authorization",
                    "access_control"})
    async def get_auth_profile(
            identifier: str,
            lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """
        Get a specific AAA (Authorization) profile from ZedCloud.

        Retrieves detailed information about a single authorization profile
        by its ID or name.

        Args:
            identifier: The ID or name of the authorization profile to retrieve.
            lookup_by: Whether to look up by "id" or "name" (default: "name").

        Returns:
            dict: Detailed authorization profile data.
            str: Error message if the profile is not found or request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("authorization-profiles-detail.json")
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for authorization profile detail not found.")
                return "Mock data for authorization profile detail not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/authorization/profiles/id/{identifier}"
        else:
            url = (f"{ZEDEDA_API_BASE}/api/v1/authorization/profiles/name/"
                   f"{urllib.parse.quote(identifier)}")

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"No authorization profile found with {lookup_by}: {identifier}."
        return response
