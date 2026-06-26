"""
Zededa MCP tools for realms management.
"""
from typing import Any, Literal, Optional
import urllib.parse
from utility.field_extractors import RealmFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, is_valid_uuid, logger
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_realm_tools(mcp):
    """ Register all realm-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"iam", "realms"})
    async def query_realms(
            summary: Optional[bool] = None,
            sfdc_id: Optional[str] = None,
            hubspot_id: Optional[str] = None,
            project: Optional[str] = None,
            name_pattern: Optional[str] = None,
            all: Optional[bool] = None,
            role_name: Optional[str] = None,
            size: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query all realms with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Return summary information only
            sfdc_id: Filter by Salesforce ID
            hubspot_id: Filter by HubSpot ID
            project: Filter by project
            name_pattern: Filter by name pattern (supports wildcards)
            all: Include all realms
            role_name: Filter by role name
            size: Filter by size
            page_token: Page token for pagination
            order_by: Fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of realms with requested fields
        """
        # Use the pre-configured RealmFieldExtractor
        field_extractor = RealmFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/realms"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("realms-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
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
                    size=size,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

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
        if order_by:
            for field in order_by:
                params.setdefault("next.orderBy", []).append(field)
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/realms"
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
            return "Failed to retrieve realms."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
    
    @mcp.tool(tags={"iam", "realms", "by_id", "by_name"})
    async def get_realm(
            identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get a specific realm by its ID or name.
            Args:
                identifier: The device ID or name to look up
                lookup_by: Search method - "id" for device ID lookup or "name" for name lookup (default: "name")
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"realms-detail.json")
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Realm with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
           # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/realms/name/{urllib.parse.quote(identifier)}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found realm by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid realm ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but realm not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/realms/name/{urllib.parse.quote(identifier)}"
        if lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/realms/id/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"realm not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
