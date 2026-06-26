"""
Zededa MCP tools for edge application management.
"""

from typing import Any, Literal, Optional
import httpx
import urllib.parse
from datetime import datetime
from utility.field_extractors import EdgeAppFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    make_zededa_request,
    ZEDEDA_API_BASE,
    USER_AGENT,
    build_query_url,
    logger,
    load_mock_json,
    is_valid_uuid
)
from mock_utils import filter_mock_list, select_mock_fields, filter_mock_by_identifier
from auth import ensure_bearer_token

try:
    from app.prompts.plot_generation_prompt import create_plot_response_structure
except ImportError:
    logger.info("Failed to import create_plot_response_structure from app.prompts.plot_generation_prompt", exc_info=True)
    # Fallback if running from different directory context
    try:
        from prompts.plot_generation_prompt import create_plot_response_structure
    except ImportError:
        logger.info("Failed to import create_plot_response_structure from prompts.plot_generation_prompt", exc_info=True)
        create_plot_response_structure = None
except Exception as e:
    logger.info(f"Unexpected error importing create_plot_response_structure: {e}", exc_info=True)
    create_plot_response_structure = None
    

def register_edge_app_tools(mcp):
    """Register all edge application-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"all_edge_apps"})
    async def get_all_edge_apps(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
        create_plot: bool = False
    ) -> dict[str, Any] | str:
        """Get all edge applications from Zededa.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Note: The `projectAccessList` field is ALWAYS empty in this list response.
        To retrieve project access information for an edge application, make a separate
        call to `get_edge_app` with the edge app's id or name — the detail response
        includes the populated `projectAccessList`.

        Args:
            page_size: Defines the page size
            page_num: Page number
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            create_plot: If True, wrap response with data and plot_instructions (plot generation instructions) for chart creation (default: False)

        Returns:
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        # Use the pre-configured EdgeAppFieldExtractor
        field_extractor = EdgeAppFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-apps-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                )
                filtered_response = field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )
                if create_plot and create_plot_response_structure:
                    metric_context = "Edge App Information. The default chart type is a pie or bar chart showing that shows version distributions."
                    return create_plot_response_structure(filtered_response, metric_context)
                return filtered_response

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve edge applications."
        
        # Filter the response using the field extractor
        filtered_response = field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

        if create_plot and create_plot_response_structure:
            logger.debug("Creating plot instructions for Edge Apps")
            metric_context = "Edge App Information. The default chart type is a pie or bar chart showing that shows version distributions."
            return create_plot_response_structure(filtered_response, metric_context)
        
        return filtered_response
    
    @mcp.tool(tags={"edge_apps_by_id", "edge_apps_by_name"})
    async def get_edge_app(
        identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get a specific edge application from Zededa by its ID.
            Args:
                identifier: The edge app ID or name to look up
                lookup_by: Search method - "id" for edge app ID lookup or "name" for name lookup (default: "name")
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"edge-apps-detail.json")
            if mock is not None:
                # Use intelligent filtering with explicit ID lookup
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Failed to retrieve edge application with {lookup_by}: {identifier}."
                return filtered_mock

        token = await ensure_bearer_token() 
        
        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/apps/name/{identifier}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found edge app by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid edge app ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but edge app not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/{lookup_endpoint}/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"edge app not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
    
    @mcp.tool(tags={"edge_apps", "projects", "access_list"})
    async def edge_app_project_access_list_by_id(
            id: str,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """
        Query the project access list of an edge application bundle by its ID.

        This tool retrieves the list of projects that have access to a specific
        edge application bundle, providing visibility into application deployment
        permissions and access control.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"edge-apps-detail.json")
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge application with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug(
            f"Invoked get_zededa_edge_app_project_list_by_id tool for app bundle ID: {id}"
        )

        # Validate required parameter
        if not id or not id.strip():
            return "Error: id (app bundle ID) is required and cannot be empty"

        # Limit page size to prevent token exhaustion
        effective_page_size = min(page_size or 20, 50)

        # Build URL - encode the ID for URL safety
        encoded_id = urllib.parse.quote(id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/id/{encoded_id}/projects"

        # Build query parameters
        params = {}

        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
            
        url = build_query_url(url, params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token,
        }
      
        logger.info(
            f"Getting project access list for app bundle ID '{id}' from: {url}"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata for context
                result["_request_info"] = {
                    "app_bundle_id": id,
                    "query_type": "project_access_list",
                    "query_timestamp": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"Edge application bundle with ID '{id}' not found"
                elif e.response.status_code == 403:
                    return f"Access denied: You don't have permission to view the project access list for edge application bundle with ID '{id}'"
                elif e.response.status_code == 400:
                    return f"Bad request: Invalid parameters provided. Error: {e.response.text}"
                else:
                    return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"
