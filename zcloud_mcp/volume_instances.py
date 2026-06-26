"""
Zededa MCP tools for volume instance management.

These tools provide agents with a comprehensive interface for querying and managing
volume instances in Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import httpx
import urllib.parse
from utility.field_extractors import (
    VolumeInstanceFieldExtractor,
    VolumeInstanceStatusFieldExtractor,
    VolumeInstanceStatusConfigFieldExtractor,
    detect_list_response_mode,
    get_swagger_schema_for_discovery
)
from utils import (
    is_valid_uuid,
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
    load_mock_json,
    get_default_time_range,
)
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token
from utils import logger

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
except Exception as e:
    logger.info("Unexpected error importing create_plot_response_structure: %s", e)
    create_plot_response_structure = None


def register_volume_instance_tools(mcp):
    """Register all volume instance-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Volume instance tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"volume_instance", "lookup_by_id_or_name"})
    async def get_volume_instance(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific volume instance.

        Use this tool when you need to get complete configuration and metadata for a volume instance.
        The tool automatically resolves the volume from either its unique ID or human-readable name.

        Args:
            identifier: The volume instance ID or name to look up
            lookup_by: Search method - "id" for volume ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing volume instance details including ID, name, device,
            project, size, and configuration. Returns error message if volume not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("volume-instances-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for volume instance {lookup_by}='{identifier}'"
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
                    return f"Volume instance not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(
                f"Invalid UUID format for '{identifier}', falling back to name lookup"
            )
            lookup_by = "name"

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/id/{identifier}"
        else:
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/name/{urllib.parse.quote(identifier)}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(
            f"Retrieving volume instance by {lookup_by}: '{identifier}'"
        )

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

    @mcp.tool(tags={"volume_instance", "status", "lookup_by_id_or_name"})
    async def get_volume_instance_status(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Get the status of an edge volume instance.

        Use this tool to retrieve runtime status information for a volume instance,
        including operational state, usage metrics, and health information.

        Args:
            identifier: The volume instance ID or name to look up
            lookup_by: Search method - "id" for volume ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing volume instance status including run state, usage,
            and operational metrics. Returns error message if volume not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("volume-instances-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for volume instance status {lookup_by}='{identifier}'"
                )
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Volume instance with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(
                f"Invalid UUID format for '{identifier}', falling back to name lookup"
            )
            lookup_by = "name"

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/id/{identifier}/status"
        else:
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/name/{urllib.parse.quote(identifier)}/status"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(
            f"Retrieving volume instance status by {lookup_by}: '{identifier}'"
        )

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


    @mcp.tool(tags={"volume_instance", "events", "lookup_by_id_or_name"})
    async def get_volume_instance_events(
            identifier: str,
            lookup_by: Literal["id", "name"] = "name",
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            severity: Optional[str] = None,
            resource: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """
        Get configuration and status events of an edge volume instance.

        Use this tool to retrieve the event history for a volume instance,
        including configuration changes, status updates, and operational events.

        Args:
            identifier: The volume instance ID or name to look up
            lookup_by: Search method - "id" for volume ID lookup or "name" for name lookup (default: "name")
            start_time: Filter events after this time (ISO 8601 format)
            end_time: Filter events before this time (ISO 8601 format)
            severity: Filter by event severity (e.g., INFO, WARNING, ERROR)
            resource: Filter by resource type
            page_token: Token for pagination
            order_by: List of fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total pages to retrieve

        Returns:
            Dictionary containing list of events for the volume instance,
            or error message if request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("volume-instances-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for volume instance events {lookup_by}='{identifier}'"
                )
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Volume instance with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(
                f"Invalid UUID format for '{identifier}', falling back to name lookup"
            )
            lookup_by = "name"

        # Build query parameters
        params = {}
        # Apply default time range if both start_time and end_time are not specified
        if start_time is None and end_time is None:
            start_time, end_time = get_default_time_range()

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if severity:
            params["severity"] = severity
        if resource:
            params["resource"] = resource
        if page_token:
            params["next.pageToken"] = page_token
        if order_by:
            for field in order_by:
                params.setdefault("next.orderBy", []).append(field)
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        if lookup_by == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/id/{identifier}/events"
        else:
            url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/name/{urllib.parse.quote(identifier)}/events"

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

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(
            f"Retrieving volume instance events by {lookup_by}: '{identifier}'"
        )

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


    @mcp.tool(tags={"volume_instances", "get_all_volume_instances"})
    async def get_all_volume_instances(
            summary: Optional[bool] = None,
            device_name: Optional[str] = None,
            project_name: Optional[str] = None,
            name_pattern: Optional[str] = None,
            label_name: Optional[str] = None,
            app_inst_name: Optional[str] = None,
            device_name_pattern: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query edge volume instances from Zedcloud with comprehensive filtering options.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            summary: Return summary information only
            device_name: Filter by exact device name
            project_name: Filter by exact project name
            name_pattern: Filter by volume name pattern (supports wildcards)
            label_name: Filter by label name
            app_inst_name: Filter by application instance name
            device_name_pattern: Filter by device name pattern
            project_name_pattern: Filter by project name pattern
            page_token: Token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total pages to retrieve
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of volume instances with requested fields,
            or error message if request fails.
        """
        # Use the pre-configured VolumeInstanceFieldExtractor
        field_extractor = VolumeInstanceFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/volumes/instances"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "volume-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for volume instances list")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    device_name=device_name,
                    project_name=project_name,
                    name_pattern=name_pattern,
                    label_name=label_name,
                    app_inst_name=app_inst_name,
                    device_name_pattern=device_name_pattern,
                    project_name_pattern=project_name_pattern,
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
        if device_name:
            params["deviceName"] = device_name
        if project_name:
            params["projectName"] = project_name
        if name_pattern:
            params["namePattern"] = name_pattern
        if label_name:
            params["labelName"] = label_name
        if app_inst_name:
            params["appInstName"] = app_inst_name
        if device_name_pattern:
            params["deviceNamePattern"] = device_name_pattern
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        # Build query parameters
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Querying volume instances from Zededa: {url}")

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

    @mcp.tool(tags={"volume_instances", "status", "plot", "visualization"})
    async def get_all_volume_instance_status(
            device_name: Optional[str] = None,
            project_name: Optional[str] = None,
            name_pattern: Optional[str] = None,
            run_state: Optional[str] = None,
            type: Optional[str] = None,
            image_name: Optional[str] = None,
            app_inst_name: Optional[str] = None,
            device_name_pattern: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            summary: Optional[bool] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None,
            create_plot: bool = False) -> dict[str, Any] | str:
        """
        Query status of edge volume instances with filtering.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            device_name: Filter by exact device name
            project_name: Filter by exact project name
            name_pattern: Filter by volume name pattern
            run_state: Filter by run state (e.g., running, stopped)
            type: Filter by volume type
            image_name: Filter by image name
            app_inst_name: Filter by application instance name
            device_name_pattern: Filter by device name pattern
            project_name_pattern: Filter by project name pattern
            page_token: Token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total pages to retrieve
            summary: Return summary information only
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            create_plot: If True, wrap the response with plot generation instructions (default: False)

        Returns:
            Dictionary containing list of volume instance statuses with requested fields,
            or error message if request fails. If create_plot is True,
            includes instructions for visualization.
        """
        # Use the pre-configured VolumeInstanceStatusFieldExtractor for status API
        field_extractor = VolumeInstanceStatusFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/volumes/instances/status"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "volume-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for volume instance status list")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    device_name=device_name,
                    project_name=project_name,
                    name_pattern=name_pattern,
                    run_state=run_state,
                    type=type,
                    image_name=image_name,
                    app_inst_name=app_inst_name,
                    device_name_pattern=device_name_pattern,
                    project_name_pattern=project_name_pattern,
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

        if device_name:
            params["deviceName"] = device_name
        if project_name:
            params["projectName"] = project_name
        if name_pattern:
            params["namePattern"] = name_pattern
        if run_state:
            params["runState"] = run_state
        if type:
            params["type"] = type
        if image_name:
            params["imageName"] = image_name
        if app_inst_name:
            params["appInstName"] = app_inst_name
        if device_name_pattern:
            params["deviceNamePattern"] = device_name_pattern
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        # Build query parameters
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if summary is not None:
            params["summary"] = str(summary).lower()

        url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/status"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info("Querying volume instance status from Zededa")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                # Filter the response using the field extractor
                filtered_result = field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )
                
                # Wrap with plot instructions if requested and function is available
                if create_plot and create_plot_response_structure:
                    logger.debug("Creating plot instructions for volume instance status")
                    metric_context = "Volume instance status data showing run states, types, sizes, and operational metrics. Default chart type is bar chart or pie chart showing distribution across run states and types."
                    return create_plot_response_structure(filtered_result, metric_context)
                
                return filtered_result

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


    @mcp.tool(tags={"volume_instances", "status_config", "plot", "visualization"})
    async def get_all_volume_instance_status_config(
            device_name: Optional[str] = None,
            project_name: Optional[str] = None,
            name_pattern: Optional[str] = None,
            run_state: Optional[str] = None,
            type: Optional[str] = None,
            image_name: Optional[str] = None,
            app_inst_name: Optional[str] = None,
            device_name_pattern: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            summary: Optional[bool] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None,
            create_plot: bool = False) -> dict[str, Any] | str:
        """
        Query status and configuration of edge volume instances.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            device_name: Filter by exact device name
            project_name: Filter by exact project name
            name_pattern: Filter by volume name pattern
            run_state: Filter by run state
            type: Filter by volume type
            image_name: Filter by image name
            app_inst_name: Filter by application instance name
            device_name_pattern: Filter by device name pattern
            project_name_pattern: Filter by project name pattern
            page_token: Token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total pages to retrieve
            summary: Return summary information only
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            create_plot: If True, wrap the response with plot generation instructions (default: False)

        Returns:
            Dictionary containing list of volume instances with both status and configuration,
            or error message if request fails. If create_plot is True,
            includes instructions for visualization.
        """
        # Use the pre-configured VolumeInstanceStatusConfigFieldExtractor for status-config API
        field_extractor = VolumeInstanceStatusConfigFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/volumes/instances/status-config"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "volume-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for volume instance status-config list")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    device_name=device_name,
                    project_name=project_name,
                    name_pattern=name_pattern,
                    run_state=run_state,
                    type=type,
                    image_name=image_name,
                    app_inst_name=app_inst_name,
                    device_name_pattern=device_name_pattern,
                    project_name_pattern=project_name_pattern,
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

        if device_name:
            params["deviceName"] = device_name
        if project_name:
            params["projectName"] = project_name
        if name_pattern:
            params["namePattern"] = name_pattern
        if run_state:
            params["runState"] = run_state
        if type:
            params["type"] = type
        if image_name:
            params["imageName"] = image_name
        if app_inst_name:
            params["appInstName"] = app_inst_name
        if device_name_pattern:
            params["deviceNamePattern"] = device_name_pattern
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        # Build query parameters
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)
        if summary is not None:
            params["summary"] = str(summary).lower()

        url = f"{ZEDEDA_API_BASE}/api/v1/volumes/instances/status-config"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info("Querying volume instance status-config from Zededa")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                
                # Filter the response using the field extractor
                filtered_result = field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )
                
                # Wrap with plot instructions if requested and function is available
                if create_plot and create_plot_response_structure:
                    logger.debug("Creating plot instructions for volume instance status-config")
                    metric_context = "Volume instance status and configuration data showing run states, types, sizes, and configuration details. Default chart type is grouped bar chart or multi-series chart showing status and config distribution."
                    return create_plot_response_structure(filtered_result, metric_context)
                
                return filtered_result

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
