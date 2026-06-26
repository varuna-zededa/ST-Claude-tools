"""
Zededa MCP tools for global edge application management.
"""
from typing import Any, Literal, Optional
import httpx
import urllib.parse
from utility.field_extractors import EdgeAppFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import ZEDEDA_API_BASE, USER_AGENT, logger, load_mock_json, is_valid_uuid, make_zededa_request
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_global_edge_app_tools(mcp):
    """Register all global edge application-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"global_edge_apps"})
    async def get_global_edge_apps(
            name_pattern: Optional[str] = None,
            origin_type: Optional[int] = None,
            category: Optional[str] = None,
            summary: Optional[bool] = None,
            app_type: Optional[str] = None,
            deployment_type: Optional[str] = None,
            app_category: Optional[list[str]] = None,
            title_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query global edge application bundles from the parent enterprise.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            name_pattern: Filter by name pattern (supports wildcards)
            origin_type: Filter by origin type
            category: Filter by category
            summary: Return summary information only
            app_type: Filter by app type
            deployment_type: Filter by deployment type
            app_category: Filter by app categories (list)
            title_pattern: Filter by title pattern (supports wildcards)
            page_token: Page token for pagination
            order_by: Fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of global edge apps with requested fields
        """
        # Use the pre-configured EdgeAppFieldExtractor (same structure as local edge apps)
        field_extractor = EdgeAppFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/global"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("global-edge-apps-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    name_pattern=name_pattern,
                    origin_type=origin_type,
                    category=category,
                    summary=summary,
                    app_type=app_type,
                    deployment_type=deployment_type,
                    app_category=app_category,
                    title_pattern=title_pattern,
                    order_by=order_by,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked get_zededa_global_edge_apps tool")

        # Define valid enum values for validation
        valid_app_types = [
            "APP_TYPE_UNSPECIFIED", "APP_TYPE_VM", "APP_TYPE_VM_RUNTIME",
            "APP_TYPE_CONTAINER", "APP_TYPE_MODULE"
        ]

        valid_deployment_types = [
            "DEPLOYMENT_TYPE_UNSPECIFIED", "DEPLOYMENT_TYPE_STAND_ALONE",
            "DEPLOYMENT_TYPE_AZURE", "DEPLOYMENT_TYPE_K3S",
            "DEPLOYMENT_TYPE_AWS", "DEPLOYMENT_TYPE_K3S_AZURE",
            "DEPLOYMENT_TYPE_K3S_AWS", "DEPLOYMENT_TYPE_VMWARE_VCE",
            "DEPLOYMENT_TYPE_VMWARE_TKG_ATTACH"
        ]

        valid_app_categories = [
            "APP_CATEGORY_UNSPECIFIED", "APP_CATEGORY_OPERATING_SYSTEM",
            "APP_CATEGORY_INDUSTRIAL", "APP_CATEGORY_EDGE_APPLICATION",
            "APP_CATEGORY_NETWORKING", "APP_CATEGORY_SECURITY",
            "APP_CATEGORY_DATA_ANALYTICS", "APP_CATEGORY_CLOUD_APPLICATION",
            "APP_CATEGORY_DEVOPS", "APP_CATEGORY_OTHERS"
        ]

        # Validate enum parameters
        if app_type and app_type not in valid_app_types:
            return f"Invalid app_type '{app_type}'. Must be one of: {', '.join(valid_app_types)}"

        if deployment_type and deployment_type not in valid_deployment_types:
            return f"Invalid deployment_type '{deployment_type}'. Must be one of: {', '.join(valid_deployment_types)}"

        if app_category:
            invalid_categories = [
                cat for cat in app_category if cat not in valid_app_categories
            ]
            if invalid_categories:
                return f"Invalid app_category values: {', '.join(invalid_categories)}. Valid categories are: {', '.join(valid_app_categories)}"

        # Limit page size to prevent token exhaustion
        effective_page_size = min(page_size or 20, 50)

        # Build query parameters
        params = {}

        if name_pattern:
            params["namePattern"] = name_pattern
        if origin_type is not None:
            params["originType"] = str(origin_type)
        if category:
            params["category"] = category
        if summary is not None:
            params["summary"] = str(summary).lower()
        if app_type:
            params["appType"] = app_type
        if deployment_type:
            params["deploymentType"] = deployment_type
        if app_category:
            for cat in app_category:
                params.setdefault("appCategory", []).append(cat)
        if title_pattern:
            params["titlePattern"] = title_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if order_by:
            for field in order_by:
                params.setdefault("next.orderBy", []).append(field)
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/global"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(
                        f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token
        }
      
        logger.info(f"Getting global edge apps from URL: {url}")

        # Make the request
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
    
    @mcp.tool(tags={"global_edge_apps", "by_id", "by_name"})
    async def get_global_edge_app(
        identifier: str, 
        lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """
        Get a specific global edge application bundle by its ID or name.
        
        Args:
            identifier: The global edge app ID or name to look up
            lookup_by: Search method - "id" for global edge app ID lookup or "name" for name lookup (default: "name")
        
        Returns:
            Global edge application details as a dictionary
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"global-edge-apps-detail.json")
            if mock is not None:
                # Use intelligent filtering with explicit ID lookup
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Failed to retrieve global edge application with ID: {id}."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug(
            f"Invoked get_global_edge_app tool for {lookup_by}: {identifier}")
        
        # Validate required parameter
        if not identifier or not identifier.strip():
            return "Error: identifier is required and cannot be empty"
        
        # Encode identifier for URL safety
        encoded_identifier = urllib.parse.quote(identifier, safe='')
        
        # Determine lookup method and build URL
        actual_lookup_method = lookup_by
        lookup_note = None
        
        # If looking up by ID but identifier is not a valid UUID, fallback to name lookup
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', falling back to name-based lookup")
            actual_lookup_method = "name"
            lookup_note = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found global edge app by name instead. For future requests, use lookup_by='name' for this global edge app."
        
        # Build URL based on determined lookup method
        lookup_endpoint = "id" if actual_lookup_method == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/global/{lookup_endpoint}/{encoded_identifier}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token
        }
        
        logger.info(f"Getting global edge app '{identifier}' (lookup_by: {actual_lookup_method}) from: {url}")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                # Add lookup note if we did a fallback
                if lookup_note:
                    result["_lookup_note"] = lookup_note
                
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"Global edge application with {actual_lookup_method} '{identifier}' not found"
                elif e.response.status_code == 403:
                    return f"Access denied: You don't have permission to access global edge application '{identifier}'"
                else:
                    return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"
