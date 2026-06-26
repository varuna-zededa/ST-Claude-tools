"""
Zededa MCP tools for roles management.

These tools provide agents with a comprehensive interface for querying and managing
IAM role information in Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import httpx
import urllib.parse
from utility.field_extractors import RoleFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    is_valid_uuid,
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
    load_mock_json,
)
from mock_utils import filter_mock_list, select_mock_fields, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_roles_tools(mcp):
    """Register all role-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Role tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"iam", "get_all_roles", "roles", "rbac", "permissions"})
    async def get_all_roles(
        summary: Optional[bool] = None,
        sfdc_id: Optional[str] = None,
        hubspot_id: Optional[str] = None,
        project: Optional[str] = None,
        name_pattern: Optional[str] = None,
        all: Optional[bool] = None,
        role_name: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Query IAM roles from Zedcloud with comprehensive filtering options.

        This tool provides flexible querying of role information with support
        for filtering by various attributes and pagination. Useful for RBAC
        (Role-Based Access Control) management.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            summary: Return summary information only (boolean)
            sfdc_id: Filter by Salesforce ID
            hubspot_id: Filter by HubSpot ID
            project: Filter by project
            name_pattern: Filter by role name pattern (supports wildcards)
            all: Include all roles regardless of permissions (boolean)
            role_name: Filter by specific role name
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of roles with metadata including IDs, names,
            and permission configurations. Returns error message on failure.
        """
        # Use the pre-configured RoleFieldExtractor
        field_extractor = RoleFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/roles"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("roles-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for roles query")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    sfdc_id=sfdc_id,
                    hubspot_id=hubspot_id,
                    project=project,
                    name_pattern=name_pattern,
                    all=all,
                    role_name=role_name,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked get_all_roles tool")

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
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/roles"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Querying roles from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"iam", "role", "rbac", "permissions", "lookup by id or name"})
    async def get_role(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific IAM role.

        Use this tool when you need to get complete configuration and metadata for a role.
        The tool automatically resolves the role from either its unique ID or human-readable name.

        Args:
            identifier: The role ID or name to look up
            lookup_by: Search method - "id" for role ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing role details including ID, name, permissions,
            and access control configuration. Returns error message if role not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("roles-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for role {lookup_by}='{identifier}'"
                )
                # Use intelligent filtering - auto-detects ID vs name, with fallback
                filtered_mock = filter_mock_by_identifier(
                    mock,
                    identifier,
                    lookup_by=lookup_by,
                    id_field="id",
                    name_field="name"
                )
                if filtered_mock is None:
                    return f"Role not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(
                f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup"
            )
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/roles/name/{urllib.parse.quote(identifier, safe='')}"
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Authorization": token,
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    result = response.json()
                    # Success with name lookup - inform the LLM
                    result["_lookup_note"] = (
                        f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found role by name instead. For future requests, use lookup_by='name' for this role."
                    )
                    return result
                except Exception as e:
                    logger.error(
                        f"Name-based lookup also failed for identifier '{identifier}': {e}"
                    )
                    # If name lookup also fails, return error
                    return f"Invalid role ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but role not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/roles/{lookup_endpoint}/{encoded_identifier}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Retrieving role {lookup_by}='{identifier}'")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"Role not found. Check that the {lookup_by} '{identifier}' is correct."
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"iam", "self_role", "rbac", "permissions", "current user"})
    async def get_role_self() -> dict[str, Any] | str:
        """
        Get the current user's role information.

        This tool retrieves the role(s) assigned to the authenticated user,
        useful for understanding current permissions and access control context.

        Returns:
            Dictionary containing the current user's role details including ID,
            name, permissions, and access control configuration.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("roles-detail.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for role self")
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/roles/self"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info("Retrieving current user's role information")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return "No role found for current user."
                elif e.response.status_code == 403:
                    return "Access denied: Unable to retrieve own role information."
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"
