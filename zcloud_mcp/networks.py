"""
Zededa MCP tools for network management.
"""
from typing import Any, Literal, Optional
from utility.field_extractors import NetworkFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, is_valid_uuid, logger
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_network_tools(mcp):
    """Register all network-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"all_networks"})
    async def get_all_networks(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """Get all networks.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
        """
        # Use the pre-configured NetworkFieldExtractor
        field_extractor = NetworkFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/networks"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("networks-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/networks?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve networks."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"networks", "by_id", "by_name"})
    async def get_network(
        identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get a specific network by its ID or name.
            Args:
                identifier: The network ID or name to look up
                lookup_by: Search method - "id" for network ID lookup or "name" for name lookup (default: "name")
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"networks-detail.json")
            if mock is not None:
                # Use intelligent filtering with explicit ID lookup
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Failed to retrieve network with {lookup_by}: {identifier}."
                return filtered_mock

        token = await ensure_bearer_token()

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/networks/name/{identifier}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found network by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid network ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but network not found. Please verify the identifier."


        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/networks/{lookup_endpoint}/{identifier}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"network not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
    