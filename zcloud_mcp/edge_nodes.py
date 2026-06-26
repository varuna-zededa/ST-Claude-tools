"""
Zededa MCP tools for edge node (device) management.

These tools provide agents with a comprehensive interface for querying, monitoring, and
analyzing edge node (device) status, metrics, and events from Zedcloud

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import httpx
import urllib.parse
from datetime import datetime
from utility.field_extractors import EdgeNodeFieldExtractor, EdgeNodeStatusConfigFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    make_zededa_request,
    is_valid_uuid,
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
    load_mock_json,
    convert_time_to_seconds,
    get_default_time_range,
)
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token

try:
    from app.prompts.plot_generation_prompt import create_plot_response_structure
except ImportError:
    logger.info("Failed to import create_plot_response_structure from app.prompts.plot_generation_prompt")
    # Fallback if running from different directory context
    try:
        from prompts.plot_generation_prompt import create_plot_response_structure
    except ImportError:
        logger.info("Failed to import create_plot_response_structure from prompts.plot_generation_prompt")
        create_plot_response_structure = None
except Exception:
    logger.info("Unexpected error importing create_plot_response_structure")
    create_plot_response_structure = None


def register_edge_node_tools(mcp):
    """Register all edge node-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Edge node tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"nodes", "edge nodes", "devices", "list"})
    async def get_edge_nodes(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        List all edge nodes (devices) from Zededa with optimized response filtering.

        IMPORTANT - Two-Step Discovery Pattern:
        When searching for specific data (location, IP addresses, network status, etc.):
        1. FIRST call with discover_schema=true to get the swagger schema showing ALL available fields
        2. Find the field containing the data you need (e.g., 'netStatusList' for network/location info)
        3. THEN call with return_basic_fields=true and additional_fields={"field_name": true}

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

        Returns:
            Dictionary containing:
            - list: Array of edge nodes with requested fields
            - summaryByState: Device state distribution summary
            - summaryByAppInstanceCount: App instance count summary
            - summaryByEVEDistribution: EVE OS version distribution
            - totalCount: Total number of devices
            - next: Pagination info
        """
        # Use the pre-configured EdgeNodeStatusConfigFieldExtractor for status-config API
        field_extractor = EdgeNodeStatusConfigFieldExtractor()

        # Detect mode based on parameters using the common helper function
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # Define the API endpoint for this tool
        API_ENDPOINT = "/api/v1/devices/status-config"
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        # This lets LLM analyze the response structure to find which fields contain needed data
        if is_discovery_mode:
            swagger_schema = get_swagger_schema_for_discovery(API_ENDPOINT)
            if swagger_schema:
                logger.info(f"Discovery mode: returning swagger schema for {API_ENDPOINT} (no API call)")
                return swagger_schema
            # If swagger unavailable, return error - do NOT fall back to API call
            logger.error(f"Swagger schema not available for {API_ENDPOINT}")
            return {"error": f"Swagger schema not available for {API_ENDPOINT}. Cannot discover field structure."}
        
        # In normal mode, use the requested page size
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-nodes-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                )
                return field_extractor.filter_response(
                    filtered_mock, 
                    additional_fields,
                    exclude_summary_keys=["summaryByEVEDistribution"],
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/status-config?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve nodes."

        # Filter the response using the field extractor to return only requested fields
        # Exclude summaryByEVEDistribution by default as it contains 100+ EVE versions and bloats the response
        return field_extractor.filter_response(
            response, 
            additional_fields,
            exclude_summary_keys=["summaryByEVEDistribution"],
            return_complete=return_complete
        )

    @mcp.tool(tags={"device", "edge_node", "node", "lookup_by_id_or_name"})
    async def get_edge_node(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific edge node.

        Use this tool when you need to get complete configuration and metadata for a device.
        The tool automatically resolves the device from either its unique ID or human-readable name.

        Args:
            identifier: The device ID or name to look up
            lookup_by: Search method - "id" for device ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing device details including ID, name, project, serial number,
            EVE version, and configuration status. Returns error message if device not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-nodes-detail.json")
            if mock is not None:
                # Use intelligent filtering - auto-detects ID vs name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/devices/name/{identifier}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found device by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid device ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but device not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/{lookup_endpoint}/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Device not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
    
    @mcp.tool(tags={"status_info", "time", "lookup_by_id_or_name"})
    async def get_edge_node_status_info(identifier: str, lookup_by: Literal["id", "name"] = "name"
                                        ) -> dict[str, Any] | str:
        """
        Retrieve detailed status information about a specific edge node. If the get_edge_node_status doesn't 
        contain the needed fields, try calling this tool. 

        Use this tool when you need d information about hardware configuration, timestamps, storage details, 
        cellular connectivity, NTP synchronization, or debugging information 
        The tool automatically resolves the device from either its unique ID or human-readable name.

        Args:
            identifier: The device ID or name to look up
            lookup_by: Search method - "id" for device ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing device status info details including ID, name, last seen time, and last booted
            time. Returns error message if device not found. NOTE: Last seen time is the lastUpdated field in the response.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-nodes-detail.json")
            if mock is not None:
                # Use intelligent filtering - auto-detects ID vs name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node with {lookup_by} '{identifier}' not found."
                return filtered_mock
        
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/devices/name/{identifier}/status/info"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found device by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid device ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but device not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/{lookup_endpoint}/{identifier}/status/info"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Device not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
    

    @mcp.tool(tags={"status_info", "time", "lookup_by_id_or_name"})
    async def get_edge_node_status(identifier: str, lookup_by: Literal["id", "name"] = "name"
                                        ) -> dict[str, Any] | str:
        """
        Retrieve detailed status information about a specific edge node. If the get_status_info doesn't 
        contain the needed fields, try calling this tool. 

    
        Args:
            identifier: The device ID or name to look up
            lookup_by: Search method - "id" for device ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing device status details of an edge node. Returns error message if device not found.
            NOTE: Last seen time is the lastUpdated field in the response.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-nodes-detail.json")
            if mock is not None:
                # Use intelligent filtering - auto-detects ID vs name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node with {lookup_by} '{identifier}' not found."
                return filtered_mock
        
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/devices/name/{identifier}/status"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found device by name instead. For future requests, use lookup_by='name' for this device."
                return response
            # If name lookup also fails, return error
            return f"Invalid device ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but device not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/{lookup_endpoint}/{identifier}/status"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Device not found. Check that the {lookup_by} '{identifier}' is correct."
        return response


    @mcp.tool(
        tags={
            "devices", "edge_nodes", "eve-distribution", "status",
            "summary", "plot", "visualization"
        })
    async def get_edge_nodes_eve_os_distribution_summary(
            max_versions: int = 15,
            create_plot: bool = False) -> dict[str, Any] | str:
        """
        Get EVE OS distribution summary across all edge nodes, aggressively transformed for LLM plot generation.

        This tool performs multi-level data reduction:
        1. Groups rare versions into 'Other'
        2. Limits to top N versions
        3. Returns JSON-ready format (~15KB for 300+ versions)

        Args:
            max_versions: Maximum number of EVE OS versions to show individually (default: 15).
            create_plot: If True, wrap response with data and plot_instructions for chart creation (default: False)

        Returns:
            dict with plot-ready EVE OS distribution data
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-nodes-summary.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info(
                    "[MOCK] Returning mock data for EVE OS distribution summary"
                )
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/devices/status?summary=true"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token,
        }
        logger.debug(f"Querying EVE OS distribution summary from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                eve_summary = result.get("summaryByEVEDistribution") or {}
                dist = eve_summary.get("values") or {}
                total = eve_summary.get("total") or 0

                # Sort versions by count descending
                sorted_versions = sorted(dist.items(), key=lambda x: x[1], reverse=True)
                top_versions = sorted_versions[:max_versions]
                other_versions = sorted_versions[max_versions:]

                # Aggregate 'Other'
                other_count = sum(v[1] for v in other_versions)

                # Build plot-ready response
                transformed = {
                    "total_nodes": total,
                    "top_versions": max_versions,
                    "data": {v: c for v, c in top_versions},
                }
                if other_count > 0:
                    transformed["data"]["Other"] = other_count

                logger.debug(
                    f"Transformed {len(dist)} EVE versions to {len(transformed['data'])} plot points"
                )
                logger.debug("is create_plot_response_structure available? %s", create_plot_response_structure is not None)
                logger.debug("create_plot parameter is %s", create_plot)
                # Wrap with plot instructions if requested and function is available
                if create_plot and create_plot_response_structure:
                    logger.debug("Creating plot instructions for EVE OS distribution")
                    metric_context = f"EVE OS version distribution across {total} edge nodes. Default chart type is pie or bar chart showing version distribution."
                    return create_plot_response_structure(transformed, metric_context)
                
                return transformed

            except Exception as e:
                logger.error(f"Error transforming EVE OS distribution: {e}")
                return f"Error transforming EVE OS distribution: {e}"

    @mcp.tool(tags={"devices", "edge_nodes", "status", "summary"})
    async def get_edge_node_status_summary() -> dict[str, Any] | str:
        """
        Get a summary of edge node status for all devices.

        Returns:
            dict containing aggregated edge node status data suitable for visualization
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-nodes-summary.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for edge node status summary")
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        # Build URL with query parameters for summary view
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/status?summary=true"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token,
        }
        logger.info(f"Querying edge node status summary from URL: {url}")

        # Make the request
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
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"devices", "edge_nodes", "status"})
    async def query_all_edge_node_status(
            summary: Optional[bool] = None,
            run_state: Optional[str] = None,
            project_name: Optional[str] = None,
            load: Optional[str] = None,
            name_pattern: Optional[str] = None,
            tags: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            device_name: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = None,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None,
            admin_state: Optional[str] = None,
            eve_lts_support_type: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query the status of edge nodes as reported by the edge nodes themselves.

        This tool provides comprehensive filtering and pagination options to query
        edge node status information from the ZedCloud platform.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            summary: Return summary information only (boolean)
            run_state: Filter by operation status. Valid values:
                      UNSPECIFIED, ONLINE, HALTED, INIT, REBOOTING, OFFLINE, UNKNOWN,
                      UNPROVISIONED, PROVISIONED, SUSPECT, DOWNLOADING, RESTARTING,
                      PURGING, HALTING, ERROR, VERIFYING, LOADING, CREATING_VOLUME,
                      BOOTING, MAINTENANCE_MODE, START_DELAYED, BASEOS_UPDATING,
                      PREPARING_POWEROFF, POWERING_OFF, PREPARED_POWEROFF
            project_name: Filter by project name
            load: Filter by device load level. Valid values: UNSPECIFIED, FREE, MODERATE, HEAVY
            name_pattern: Filter by device name pattern (supports wildcards)
            tags: Filter by device tags (JSON stringified key-value pairs)
            project_name_pattern: Filter by project name pattern (supports wildcards)
            device_name: Filter by specific device name
            page_token: Page token for pagination
            page_num: Page number for pagination
            page_size: Number of items per page (default: 20, max: 50 to prevent token exhaustion)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            admin_state: Filter by administrative state. Valid values:
                        UNSPECIFIED, CREATED, DELETED, ACTIVE, INACTIVE, REGISTERED, ARCHIVED
            eve_lts_support_type: Filter by EVE version support type. Valid values:
                                 SUPPORT_TYPE_UNSPECIFIED, SUPPORT_TYPE_LTS, SUPPORT_TYPE_NON_LTS

        Returns:
            Dictionary containing:
            - list: Array of edge nodes with requested fields
            - summaryByState: Device state distribution summary
            - summaryByAppInstanceCount: App instance count summary
            - summaryByEVEDistribution: EVE OS version distribution
            - totalCount: Total number of devices
            - next: Pagination info
        """
        # Use the pre-configured EdgeNodeFieldExtractor from utility.field_extractors
        field_extractor = EdgeNodeFieldExtractor()

        # Detect mode based on parameters using the common helper function
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # Define the API endpoint for this tool
        API_ENDPOINT = "/api/v1/devices/status"
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        # This lets LLM analyze the response structure to find which fields contain needed data
        if is_discovery_mode:
            swagger_schema = get_swagger_schema_for_discovery(API_ENDPOINT)
            if swagger_schema:
                logger.info(f"Discovery mode: returning swagger schema for {API_ENDPOINT} (no API call)")
                return swagger_schema
            # If swagger unavailable, return error - do NOT fall back to API call
            logger.error(f"Swagger schema not available for {API_ENDPOINT}")
            return {"error": f"Swagger schema not available for {API_ENDPOINT}. Cannot discover field structure."}
        
        # In normal mode, use the requested page size
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-nodes-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    run_state=run_state,
                    project_name=project_name,
                    load=load,
                    name_pattern=name_pattern,
                    tags=tags,
                    project_name_pattern=project_name_pattern,
                    device_name=device_name,
                    admin_state=admin_state,
                    eve_lts_support_type=eve_lts_support_type,
                )
                # Apply field extraction using the field extractor
                # Exclude summaryByEVEDistribution by default as it contains 100+ EVE versions
                return field_extractor.filter_response(
                    filtered_mock, 
                    additional_fields,
                    exclude_summary_keys=["summaryByEVEDistribution"],
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked query_edge_node_status tool")

        # Define valid enum values for validation
        valid_run_states = [
            "UNSPECIFIED",
            "ONLINE",
            "HALTED",
            "INIT",
            "REBOOTING",
            "OFFLINE",
            "UNKNOWN",
            "UNPROVISIONED",
            "PROVISIONED",
            "SUSPECT",
            "DOWNLOADING",
            "RESTARTING",
            "PURGING",
            "HALTING",
            "ERROR",
            "VERIFYING",
            "LOADING",
            "CREATING_VOLUME",
            "BOOTING",
            "MAINTENANCE_MODE",
            "START_DELAYED",
            "BASEOS_UPDATING",
            "PREPARING_POWEROFF",
            "POWERING_OFF",
            "PREPARED_POWEROFF",
        ]

        valid_load_states = ["UNSPECIFIED", "FREE", "MODERATE", "HEAVY"]

        valid_admin_states = [
            "UNSPECIFIED",
            "CREATED",
            "DELETED",
            "ACTIVE",
            "INACTIVE",
            "REGISTERED",
            "ARCHIVED",
        ]

        valid_eve_support_types = [
            "SUPPORT_TYPE_UNSPECIFIED",
            "SUPPORT_TYPE_LTS",
            "SUPPORT_TYPE_NON_LTS",
        ]

        # Validate enum parameters
        if run_state and run_state not in valid_run_states:
            return f"Invalid run_state '{run_state}'. Must be one of: {', '.join(valid_run_states)}"

        if load and load not in valid_load_states:
            return (
                f"Invalid load '{load}'. Must be one of: {', '.join(valid_load_states)}"
            )

        if admin_state and admin_state not in valid_admin_states:
            return f"Invalid admin_state '{admin_state}'. Must be one of: {', '.join(valid_admin_states)}"

        if eve_lts_support_type and eve_lts_support_type not in valid_eve_support_types:
            return f"Invalid eve_lts_support_type '{eve_lts_support_type}'. Must be one of: {', '.join(valid_eve_support_types)}"

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if run_state:
            params["runState"] = run_state
        if project_name:
            params["projectName"] = project_name
        if load:
            params["load"] = load
        if name_pattern:
            params["namePattern"] = name_pattern
        if tags:
            params["tags"] = tags
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if device_name:
            params["deviceName"] = device_name
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if admin_state:
            params["adminState"] = admin_state
        if eve_lts_support_type:
            params["eveLtsSupportType"] = eve_lts_support_type

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/status"

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

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token,
        }

        logger.info(f"Querying edge node status from URL: {url}")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Filter the response using the field extractor to return only requested fields
                # Exclude summaryByEVEDistribution by default as it contains 100+ EVE versions
                return field_extractor.filter_response(
                    result, 
                    additional_fields,
                    exclude_summary_keys=["summaryByEVEDistribution"],
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

    @mcp.tool(tags={"device", "metrics", "timeseries", "monitoring"})
    async def get_edge_node_metrics(
        identifier: str,
        metric_type: str,
        lookup_by: Literal["id", "name"] = "name",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        create_plot: bool = False,
    ) -> dict[str, Any] | str:
        """
        Retrieve historical resource usage metrics for an edge node.

        This tool provides time-series data for device performance analysis, capacity planning,
        and troubleshooting performance issues.

        Common Use Cases:
        - Analyze CPU/memory trends before scaling applications
        - Investigate performance anomalies in logs
        - Plan maintenance windows based on usage patterns
        - Generate performance reports for stakeholders

        Args:
            identifier: Device/Edge node ID or name
            metric_type: Type of metric to retrieve (required). Valid options:
                        CPU_TOTAL, CPU_USAGE, MEMORY_TOTAL, MEMORY_UTILIZATION,
                        NETWORK_TOTAL, NETWORK_RATES, STORAGE_UTILIZATION,
                        STORAGE_IO_ZPOOL, STORAGE_IO_ZVOL, EVENTS_COUNT
                        Note: "usage" and "utilization" are often used interchangeably.
                        Use CPU_USAGE for CPU utilization, MEMORY_UTILIZATION for memory usage.
            lookup_by: "id" for device ID or "name" for device name (default: "name")
            start_time: Start time in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
            end_time: End time in ISO 8601 format (e.g., "2024-01-01T23:59:59Z")
            interval: Time interval/granularity for data points in ISO 8601 duration format (e.g., "PT1H" for 1 hour)
            create_plot: If True, wrap response with data and plot_instructions (plot generation instructions) for chart creation (default: False)

        Returns:
            Dictionary containing:
            - data: Array of timestamp-value pairs
            - _summary: Metadata including data point count and time range
            - _request_info: Echo of request parameters for context
            - If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-nodes-metrics.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock metrics data for device {lookup_by}='{identifier}', metric: {metric_type}"
                )
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Metrics for edge node with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameters
        if not identifier or not identifier.strip():
            return f"Error: identifier ({lookup_by}) is required and cannot be empty"

        # Validate UUID if looking up by id - if invalid, try as name instead
        original_lookup_by = lookup_by
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}' in metrics request, attempting name-based lookup")
            lookup_by = "name"  # Override to use name-based lookup

        if not metric_type or not metric_type.strip():
            return "Error: metric_type is required"

        # Valid metric types from API
        valid_metrics = {
            "UNSPECIFIED",
            "CPU_TOTAL",
            "CPU_USAGE",
            "MEMORY_TOTAL",
            "MEMORY_UTILIZATION",
            "NETWORK_TOTAL",
            "NETWORK_RATES",
            "EVENTS_COUNT",
            "STORAGE_UTILIZATION",
            "STORAGE_IO_ZPOOL",
            "STORAGE_IO_ZVOL",
        }

        if metric_type not in valid_metrics:
            return f"Invalid metric_type '{metric_type}'. Try one of: {', '.join(sorted(valid_metrics))}"

        # Validate time formats if provided
        if start_time:
            try:
                datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                return f"Invalid start_time format. Use ISO 8601 format like '2024-01-01T00:00:00Z'"

        if end_time:
            try:
                datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return f"Invalid end_time format. Use ISO 8601 format like '2024-01-01T23:59:59Z'"
        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/{lookup_endpoint}/{encoded_identifier}/timeSeries/{metric_type}"

        # Build query parameters
        query_params = []
        if start_time:
            query_params.append(f"startTime={urllib.parse.quote(start_time)}")
        if end_time:
            query_params.append(f"endTime={urllib.parse.quote(end_time)}")
        if interval:
            query_params.append(f"interval={urllib.parse.quote(interval)}")

        if query_params:
            url += "?" + "&".join(query_params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(
            f"Retrieving {metric_type} metrics for device {lookup_by}='{identifier}'"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add helpful context metadata
                result["_request_info"] = {
                    "device_identifier": identifier,
                    "lookup_method": lookup_by,
                    "metric_type": metric_type,
                    "start_time": start_time,
                    "end_time": end_time,
                    "interval": interval,
                    "query_time": datetime.now().isoformat(),
                }

                # Add data summary if available
                if isinstance(result, dict) and "data" in result:
                    data_points = result.get("data", [])
                    result["_summary"] = {
                        "total_data_points": len(data_points),
                        "time_range": {
                                "first": (
                                    data_points[0].get("timestamp")
                                    if data_points
                                    else None
                                ),
                                "last": (
                                    data_points[-1].get("timestamp")
                                    if data_points
                                    else None
                                ),
                        },
                    }

                # Add note if we auto-corrected from id to name lookup
                if original_lookup_by == "id" and lookup_by == "name":
                    result["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully retrieved metrics using name-based lookup instead. For future requests, use lookup_by='name' for this device."

                # Wrap with plot instructions if requested and function is available
                if create_plot and create_plot_response_structure:
                    metric_context = f"Time-series metric data for {metric_type} on device '{identifier}'. Default chart type is line. Use this guidance only if user requested a different chart type."
                    return create_plot_response_structure(result, metric_context)

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving metrics: {e}")
                return f"Network error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Device not found. Check the {lookup_by} and metric_type."
                elif e.response.status_code == 403:
                    return "Access denied to metrics data."
                elif e.response.status_code == 400:
                    return f"Bad request. Check parameters: {e.response.text}"
                else:
                    return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"device", "edge_node", "events", "status"})
    async def get_edge_node_events(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        resource: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
        total_pages: Optional[int] = None,
    ) -> dict[str, Any] | str:
        """
        Get configuration and status events of an edge node.

        This tool retrieves historical events and status changes for a specific edge node
        over a specified time period, providing insights into device configuration changes,
        status updates, and system events.

        Args:
            identifier: Edge node ID or name (required)
            lookup_by: "id" for device ID or "name" for device name (default: "name")
            start_time: Start time for events query in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
            end_time: End time for events query in ISO 8601 format (e.g., "2024-01-01T23:59:59Z")
            resource: Filter by resource type
            page_token: Page token for pagination
            page_num: Page number (starting from 1)
            page_size: Number of items per page (default: 20)
            total_pages: Total number of pages to fetch

        Returns:
            EventQueryResponse containing edge node events with timestamps and descriptions
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-nodes-events.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info(f"[MOCK] Returning mock events data for device: {identifier}")
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Events for edge node with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug(f"Invoked get_edge_node_events tool for device: {identifier}")

        # Validate required parameter
        if not identifier or not identifier.strip():
            return f"Error: identifier ({lookup_by}) is required and cannot be empty"

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}' in events request, attempting name-based lookup")
            lookup_by = "name"  # Override to use name-based lookup

        # Always resolve to device ID - events endpoint works reliably only with ID
        if lookup_by == "name":
            logger.info(f"Resolving device name '{identifier}' to ID for events lookup")
            device_url = f"{ZEDEDA_API_BASE}/api/v1/devices/name/{urllib.parse.quote(identifier, safe='')}"
            device_response = await make_zededa_request(device_url, "get", token)
            if device_response is None:
                return f"Device with name '{identifier}' not found. Cannot retrieve events."
            device_id = device_response.get("id")
            if not device_id:
                return f"Device with name '{identifier}' found but has no ID in response. Cannot retrieve events."
            logger.info(f"Resolved device name '{identifier}' to ID '{device_id}'")
        else:
            device_id = identifier

        # Build URL using device ID
        encoded_id = urllib.parse.quote(device_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/devices/id/{encoded_id}/events"
        # Apply default time range if both start_time and end_time are not specified
        if start_time is None and end_time is None:
            start_time, end_time = get_default_time_range()
        # Build query parameters
        query_params = []
        if start_time:
            # Convert ISO 8601 timestamp to seconds from epoch
            start_time_seconds = convert_time_to_seconds(start_time)
            query_params.append(f"startTime.seconds={start_time_seconds}")
        if end_time:
            # Convert ISO 8601 timestamp to seconds from epoch
            end_time_seconds = convert_time_to_seconds(end_time)
            query_params.append(f"endTime.seconds={end_time_seconds}")
        if resource:
            query_params.append(f"resource={urllib.parse.quote(resource)}")
        if page_token:
            query_params.append(f"next.pageToken={urllib.parse.quote(page_token)}")
        if page_num is not None:
            query_params.append(f"next.pageNum={page_num}")
        if page_size is not None:
            query_params.append(f"next.pageSize={page_size}")
        if total_pages is not None:
            query_params.append(f"next.totalPages={total_pages}")

        if query_params:
            url += "?" + "&".join(query_params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Getting events for device id='{device_id}' (original: {lookup_by}='{identifier}')")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request for context
                result["_request_info"] = {
                    "device_identifier": identifier,
                    "device_id": device_id,
                    "lookup_method": lookup_by,
                    "start_time": start_time,
                    "end_time": end_time,
                    "resource_filter": resource,
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
                    return f"Device with {lookup_by} '{identifier}' not found or no events data available"
                elif e.response.status_code == 403:
                    return f"Access denied: You don't have permission to access events for device '{identifier}'"
                elif e.response.status_code == 400:
                    return (
                        f"Bad request: Check your parameters. Error: {e.response.text}"
                    )
                else:
                    return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"
