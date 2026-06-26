"""
Zededa MCP tools for brand management.

These tools provide agents with a comprehensive interface for querying and
managing hardware brand information from Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single tool to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import urllib.parse
from utility.field_extractors import BrandFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, logger, load_mock_json
from auth import ensure_bearer_token


def register_brand_tools(mcp):
    """Register all brand-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Brand tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"brand", "hardware", "lookup_by_id_or_name"})
    async def get_brand(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name",
        enterprise_id: Optional[str] = None
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific hardware brand.

        Use this tool when you need to get complete information for a brand.
        The tool automatically resolves the brand from either its unique ID or human-readable name.

        Args:
            identifier: The brand ID or name to look up
            lookup_by: Search method - "id" for brand ID lookup or "name" for name lookup (default: "name")
            enterprise_id: Deprecated field: EnterpriseId

        Returns:
            Dictionary containing brand details including ID, name, and configuration.
            Returns error message if brand not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"brands-detail.json")
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for brand {lookup_by}={identifier}")
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return f"Error: identifier parameter is required and cannot be empty"

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/brands/{lookup_endpoint}/{encoded_identifier}"

        # Add query parameters if provided
        query_params = []
        if enterprise_id:
            query_params.append(f"enterpriseId={urllib.parse.quote(enterprise_id)}")

        if query_params:
            url += "?" + "&".join(query_params)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Brand not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"global_brand", "hardware", "lookup_by_id_or_name"})
    async def get_global_brand(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name",
        enterprise_id: Optional[str] = None
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific global hardware brand.

        Use this tool when you need to get complete information for a global brand.
        The tool automatically resolves the brand from either its unique ID or human-readable name.

        Args:
            identifier: The brand ID or name to look up
            lookup_by: Search method - "id" for brand ID lookup or "name" for name lookup (default: "name")
            enterprise_id: Deprecated field: EnterpriseId

        Returns:
            Dictionary containing global brand details including ID, name, and configuration.
            Returns error message if brand not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"brands-global-detail.json")
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for global brand {lookup_by}={identifier}")
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return f"Error: identifier parameter is required and cannot be empty"

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/brands/global/{lookup_endpoint}/{encoded_identifier}"

        # Add query parameters if provided
        query_params = []
        if enterprise_id:
            query_params.append(f"enterpriseId={urllib.parse.quote(enterprise_id)}")

        if query_params:
            url += "?" + "&".join(query_params)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Global brand not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
    
    @mcp.tool(tags={"brands", "hardware"})
    async def get_all_brands(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            origin_type: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = None,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query hardware brand records from Zededa with optimized response filtering.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Only summary of the records required (boolean)
            name_pattern: Brand name pattern to be matched (supports wildcards)
            origin_type: Origin of object. Valid values:
                        ORIGIN_UNSPECIFIED, ORIGIN_IMPORTED, ORIGIN_LOCAL, 
                        ORIGIN_GLOBAL, ORIGIN_APP_PROFILE_LOCAL
            page_token: Page token for pagination
            page_num: Page number for pagination
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of brands with requested fields.
        """
        # Use the pre-configured BrandFieldExtractor
        field_extractor = BrandFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/brands"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            logger.info(
                "[MOCK] Mock mode enabled, attempting to load mock data")
            mock = load_mock_json("brands-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for brands list")
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked get_all_brands tool")

        # Valid origin types
        valid_origin_types = [
            "ORIGIN_UNSPECIFIED", "ORIGIN_IMPORTED", "ORIGIN_LOCAL",
            "ORIGIN_GLOBAL", "ORIGIN_APP_PROFILE_LOCAL"
        ]

        # Validate origin_type if provided
        if origin_type and origin_type not in valid_origin_types:
            return f"Invalid origin_type '{origin_type}'. Must be one of: {', '.join(valid_origin_types)}"

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if origin_type:
            params["originType"] = origin_type
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/brands"

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

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve hardware brands."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"all_global_brands","hardware"})
    async def get_all_global_brands(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            origin_type: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = None,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query global hardware brand records from Zededa with optimized response filtering.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Only summary of the records required (boolean)
            name_pattern: Brand name pattern to be matched (supports wildcards)
            origin_type: Origin of object. Valid values:
                        ORIGIN_UNSPECIFIED, ORIGIN_IMPORTED, ORIGIN_LOCAL, 
                        ORIGIN_GLOBAL, ORIGIN_APP_PROFILE_LOCAL
            page_token: Page token for pagination
            page_num: Page number for pagination
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of global brands with requested fields.
        """
        # Use the pre-configured BrandFieldExtractor
        field_extractor = BrandFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/brands/global"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("brands-global-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked get_all_global_brands tool")

        # Valid origin types
        valid_origin_types = [
            "ORIGIN_UNSPECIFIED", "ORIGIN_IMPORTED", "ORIGIN_LOCAL",
            "ORIGIN_GLOBAL", "ORIGIN_APP_PROFILE_LOCAL"
        ]

        # Validate origin_type if provided
        if origin_type and origin_type not in valid_origin_types:
            return f"Invalid origin_type '{origin_type}'. Must be one of: {', '.join(valid_origin_types)}"

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if origin_type:
            params["originType"] = origin_type
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/brands/global"

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

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve global hardware brands."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
