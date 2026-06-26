"""
Zededa MCP tools for datastore management.
"""
from typing import Any, Literal, Optional
import urllib.parse
from utility.field_extractors import DatastoreFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, is_valid_uuid, logger
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_datastore_tools(mcp):
    """Register all datastore-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"get_all_datastores"})
    async def get_all_datastores(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """Get all datastores.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Note: The `projectAccessList` field is ALWAYS empty in this list response.
        To retrieve project access information for a datastore, make a separate call to
        `get_datastore` with the datastore's id or name — the detail response includes
        the populated `projectAccessList`.

        Args:
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
        """
        # Use the pre-configured DatastoreFieldExtractor
        field_extractor = DatastoreFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/datastores"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("datastores-list.json",
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
        url = f"{ZEDEDA_API_BASE}/api/v1/datastores?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve datastores."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"get_datastore_by_id", "get_datastore_by_name"})
    async def get_datastore( identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get detailed information about a specific datastore.
        Args:
            identifier: The datastore ID or name to look up
            lookup_by: Search method - "id" for datastore ID lookup or "name" for name lookup (default: "name")"""
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"datastores-detail.json")
            if mock is not None:
                # Use intelligent filtering - auto-detects ID vs name, with fallback
                filtered_mock = filter_mock_by_identifier(
                    mock,
                    identifier,
                    lookup_by=lookup_by,
                    id_field="id",
                    name_field="name"
                )
                if filtered_mock is None:
                    return f"Datastore not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock
        
        token = await ensure_bearer_token()

        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url =  f"{ZEDEDA_API_BASE}/api/v1/datastores/name/{identifier}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found datastore by name instead. For future requests, use lookup_by='name' for this datastore."
                return response
            # If name lookup also fails, return error
            return f"Invalid datastore ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but datastore not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/datastores/{lookup_endpoint}/{identifier}"
        logger.debug(f"lookup endpoint, {lookup_endpoint}")
        logger.debug(f"id, {identifier}")

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Datastore not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"datastores_by_project_access_list"})
    async def query_datastore_project_access_list(
            ids: Optional[list[str]] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """DO NOT USE for retrieving projectAccessList for datastores. This bulk
        endpoint is unreliable on current ZedCloud deployments and frequently returns
        400. To retrieve project access information for a datastore, call
        `get_datastore` with the datastore's id or name — the detail response
        includes the populated `projectAccessList`."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("datastores-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    ids=ids,
                )
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if ids:
            for id_val in ids:
                params.setdefault("ids", []).append(id_val)
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/datastores/projects"
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
            return "Failed to retrieve datastore project list."
        return response
