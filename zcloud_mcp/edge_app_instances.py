"""
Zededa MCP tools for edge application instance management.
"""

from typing import Any, Literal, Optional
import json
import httpx
import urllib.parse
from datetime import datetime
from utility.field_extractors import EdgeAppInstanceFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    make_zededa_request,
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
    format_app_instance,
    truncate_response,
    convert_time_to_seconds,
    load_mock_json,
    get_default_time_range,
    is_valid_uuid
)
from mock_utils import filter_mock_list, select_mock_fields, filter_mock_by_identifier, filter_mock_time_series
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
except Exception as e:
    logger.info(f"Unexpected error importing create_plot_response_structure: {e}", exc_info=True)    
    create_plot_response_structure = None

def register_edge_app_instance_tools(mcp):
    """Register all edge application instance-related MCP tools."""
    
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"app_instances_status_by_id"})
    async def edge_app_instance_status_from_id(app_instance_id: str) -> dict[str, Any] | str:
        """Get the status of a specific edge app instance by its id. Use when you only need the status of a specific edge app."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-app-instances-detail.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering with explicit ID lookup
                filtered_mock = filter_mock_by_identifier(
                    mock, app_instance_id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Failed to retrieve app instance with ID: {app_instance_id}."
                return filtered_mock
        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/id/{app_instance_id}/status"
        response = await make_zededa_request(url, "get", token)
        # format_app_instance is not used here as the status endpoint response
        # might not be a full app instance object compatible with the formatter.
        # Returning raw JSON provides more flexibility.
        return response

    @mcp.tool(tags={"app_instances_summary"})
    async def edge_app_instances_summary(create_plot: bool = False) -> dict[str, Any] | str:
        """
        Get a summary count of all edge app instances by status. Returns application instance config and application instance status
        If user asks to plot the edge app instances summary by status, make sure to set create_plot to True. 
        Args:
            create_plot: If True, wrap response with data and plot_instructions for chart creation (default: False)

        Returns:
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}

        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-app-instances-summary.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return json.dumps(mock, indent=2)
            
        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status-config?summary=true"
        response = await make_zededa_request(url, "get", token)
        if response is None or "list" not in response:
            return "Failed to retrieve app instances or response format is unexpected."
        result = json.dumps(response, indent=2)
        if create_plot and create_plot_response_structure:
            logger.debug("Creating plot instructions for Edge App distribution")
            metric_context = f"Edge App Distribution across Edge nodes. Default chart type is pie or bar chart showing version distribution."
            return create_plot_response_structure(result, metric_context)
        return result
    

    @mcp.tool(tags={"get_all_app_instances"})
    async def all_edge_app_instances(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """Get comprehensive information about all edge app instances. Only use when you need detailed information about all edge application instances.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            page_size: Number of items per page (default: 20, max: 50 to prevent token exhaustion)
            page_num: Page number for pagination 
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
        """
        # Use the pre-configured EdgeAppInstanceFieldExtractor
        field_extractor = EdgeAppInstanceFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/instances/status-config"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
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
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status-config?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        logger.debug("Invoked get_zededa_app_instances")
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve app instances."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
    
    @mcp.tool(tags={"app_instances", "get_status"})
    async def query_edge_app_instance_status(
        summary: Optional[bool] = None,
        app_instance_name: Optional[str] = None,
        run_state: Optional[str] = None,
        device_name: Optional[str] = None,
        project_name: Optional[str] = None,
        name_pattern: Optional[str] = None,
        type: Optional[int] = None,
        tags: Optional[str] = None,
        project_name_pattern: Optional[str] = None,
        device_name_pattern: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
        patch_envelope_name_pattern: Optional[str] = None,
        patch_envelope_reference: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """
        Get all edge application instances statuses with comprehensive filtering options.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            summary: App instance summary flag
            app_instance_name: User defined name of the app instance
            run_state: Operation status (UNSPECIFIED, ONLINE, HALTED, INIT, REBOOTING, OFFLINE, UNKNOWN,
                      UNPROVISIONED, PROVISIONED, SUSPECT, DOWNLOADING, RESTARTING, PURGING, HALTING,
                      ERROR, VERIFYING, LOADING, CREATING_VOLUME, BOOTING, MAINTENANCE_MODE,
                      START_DELAYED, BASEOS_UPDATING, PREPARING_POWEROFF, POWERING_OFF, PREPARED_POWEROFF)
            device_name: User defined name of the device
            project_name: User defined name of the project
            name_pattern: Name pattern for filtering
            type: Type of app (integer)
            tags: JSON stringified key value pairs
            project_name_pattern: Project name pattern
            device_name_pattern: Device name pattern
            page_token: Page token for pagination
            page_num: Page number (default: 1)
            page_size: Page size (default: 20, max: 50)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            patch_envelope_name_pattern: Patch envelope name pattern
            patch_envelope_reference: App instance patch envelope reference check
                                     (UNSPECIFIED, REFERENCING_PATCH, NOT_REFERENCING_PATCH)
        """
        # Use the pre-configured EdgeAppInstanceFieldExtractor for both status APIs
        field_extractor = EdgeAppInstanceFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/instances/status"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-detail.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )
            
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        logger.debug("Invoked query_zededa_app_instance_status tool")
        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if app_instance_name:
            params["appName"] = app_instance_name
        if run_state:
            params["runState"] = run_state
        if device_name:
            params["deviceName"] = device_name
        if project_name:
            params["projectName"] = project_name
        if name_pattern:
            params["namePattern"] = name_pattern
        if type is not None:
            params["type"] = str(type)
        if tags:
            params["tags"] = tags
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if device_name_pattern:
            params["deviceNamePattern"] = device_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        # Build query parameters
        params["next.pageSize"] = str(effective_page_size)
        if patch_envelope_name_pattern:
            params["patchEnvelopeNamePattern"] = patch_envelope_name_pattern
        if patch_envelope_reference:
            params["patchEnvelopeReference"] = patch_envelope_reference

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"

        # Add custom headers if needed
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
            "Authorization": token,
        }

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


    @mcp.tool(tags={"app_instances_status"})
    async def edge_app_instances_by_status(run_state: str, page_size: Optional[int] = 20, page_num: Optional[int] = 1) -> str:
        """Get edge app instances filtered by status, Use when you know which status you want to filter by. ex. all oneline edge apps
          run_state: Filter by operation status. Valid values:
                      UNSPECIFIED, ONLINE, HALTED, INIT, REBOOTING, OFFLINE, UNKNOWN,
                      UNPROVISIONED, PROVISIONED, SUSPECT, DOWNLOADING, RESTARTING,
                      PURGING, HALTING, ERROR, VERIFYING, LOADING, CREATING_VOLUME,
                      BOOTING, MAINTENANCE_MODE, START_DELAYED, BASEOS_UPDATING,
                      PREPARING_POWEROFF, POWERING_OFF, PREPARED_POWEROFF
            page_size: Number of items per page (default: 20, max: 50 to prevent token exhaustion)
            page_num: Page number for pagination """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                # Apply filtering to mock data
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    run_state=run_state,
                )
                return json.dumps(filtered_mock, indent=2)
            
        token = await ensure_bearer_token()
        # Limit page size to prevent large responses
        effective_page_size = min(page_size or 20, 50)
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status?runState={run_state}&next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)

        if response is None:
            return f"Failed to retrieve app instances with status: {run_state}."

        if "list" not in response:
            return f"No app instances found with status: {run_state}."

        app_instances = response["list"]
        if not app_instances:
            return f"No app instances found with status: {run_state}."

        formatted_instances = [
            format_app_instance(instance) for instance in app_instances
        ]
        result = f"App Instances with status '{run_state}':\n\n" + "\n--\n".join(
            formatted_instances
        )

        return truncate_response(result)

    @mcp.tool(tags={"edge_app_instances_by_project"})
    async def edge_app_instances_by_project(project_name: str, page_size: Optional[int] = 20, page_num: Optional[int] = 1) -> str:
        """Get edge app instances filtered by project name. More efficient than getting all instances and use when you know which project has the required edge app instances.
        project_name: User defined name of the project, unique across the enterprise. Once project is created, name can’t be changed"""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                # Apply filtering to mock data
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    project_name=project_name,
                )
                return json.dumps(filtered_mock, indent=2)
            
        token = await ensure_bearer_token()
        effective_page_size = min(page_size or 20, 50)
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status?projectName={project_name}&next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)

        if response is None:
            return f"Failed to retrieve app instances for project: {project_name}."

        if "list" not in response:
            return f"No app instances found for project: {project_name}."

        app_instances = response["list"]
        if not app_instances:
            return f"No app instances found for project: {project_name}."

        formatted_instances = [
            format_app_instance(instance) for instance in app_instances
        ]
        result = f"App Instances in project '{project_name}':\n\n" + "\n--\n".join(
            formatted_instances
        )

        return truncate_response(result)

    @mcp.tool(tags={"edge_app_instances logs by id", "app instances logs by id", "edge app instance logs"})
    async def edge_app_instance_logs_by_id(
        app_instance_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
        total_pages: Optional[int] = None
    ) -> str:
        """
        Get logs for a specific app instance from by its id.

        Args:
            app_instance_id: System defined universally unique Id of the app instance
            start_time: Start time for querying the app instance logs (ISO 8601 format or Unix timestamp)
            end_time: End time for querying the app instance logs (ISO 8601 format or Unix timestamp)
            interval: Interval at which logs need to be fetched (ISO 8601 format)
            page_token: Page token for pagination
            page_num: Page number
            page_size: Defines the page size
            total_pages: Total number of pages to be fetched
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"edge-app-instances-logs.json")
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, app_instance_id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Logs for app instance with ID '{app_instance_id}' not found."
                return json.dumps(filtered_mock, indent=2)

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/id/{app_instance_id}/logs"

        # Apply default time range if both start_time and end_time are not specified
        if start_time is None and end_time is None:
            start_time, end_time = get_default_time_range()
        # Build query parameters
        query_params = []

        # Convert time parameters to seconds and use correct parameter names
        if start_time:
            start_time_seconds = convert_time_to_seconds(start_time)
            query_params.append(f"startTime.seconds={start_time_seconds}")

        if end_time:
            end_time_seconds = convert_time_to_seconds(end_time)
            query_params.append(f"endTime.seconds={end_time_seconds}")
        
        if interval:
            query_params.append(f"interval={urllib.parse.quote(interval)}")
        if page_token:
            query_params.append(f"Cursor.pageToken={urllib.parse.quote(page_token)}")
        if page_num is not None:
            query_params.append(f"Cursor.pageNum={page_num}")
        if page_size is not None:
            query_params.append(f"Cursor.pageSize={page_size}")
        if total_pages is not None:
            query_params.append(f"Cursor.totalPages={total_pages}")

        # Add query parameters to URL if any exist
        if query_params:
            url += "?" + "&".join(query_params)

        logger.info(
            f"Fetching logs for app instance ID: {app_instance_id} from URL: {url}"
        )
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return (
                f"Failed to retrieve logs for app instance with ID: {app_instance_id}."
            )
        # Convert the response to a JSON string since MCP tools must return strings
        try:
            return json.dumps(response, indent=2)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize response to JSON: {e}")
            return f"Failed to serialize logs response for app instance with ID: {app_instance_id}."

    @mcp.tool(tags={"edge_app_instances events by id", "app instances events by id", "edge app instance events"})
    async def edge_app_instance_events_by_id(
        app_instance_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        severity: Optional[str] = None,
        resource: Optional[str] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> str:
        """
        Get configuration and status events of an edge application instance by id.

        Args:
            app_instance_id: Object id (System defined universally unique Id of the app instance)
            start_time: Start time in timestamp (ISO 8601 format or Unix timestamp)
            end_time: End time (ISO 8601 format or Unix timestamp)
            resource: Resource filter for events
            page_token: Page token for pagination
            page_num: Page number
            page_size: Defines the page size
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"edge-app-instances-events.json")
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, app_instance_id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Events for app instance with ID '{app_instance_id}' not found."
                return json.dumps(filtered_mock, indent=2)

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/id/{app_instance_id}/events"

        # Apply default time range if both start_time and end_time are not specified
        if start_time is None and end_time is None:
            start_time, end_time = get_default_time_range()
        # Build query parameters
        query_params = []

        # Convert time parameters to seconds if needed (based on API requirements)
        if start_time:
            start_time_seconds = convert_time_to_seconds(start_time)
            query_params.append(f"startTime.seconds={start_time_seconds}")

        if end_time:
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
       
        # Add query parameters to URL if any exist
        if query_params:
            url += "?" + "&".join(query_params)

        logger.info(
            f"Fetching events for app instance ID: {app_instance_id} from URL: {url}"
        )
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve events for app instance with ID: {app_instance_id}."

        # Convert the response to a JSON string since MCP tools must return strings
        try:
            return json.dumps(response, indent=2)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize response to JSON: {e}")
            return f"Failed to serialize events response for app instance with ID: {app_instance_id}."

   
    @mcp.tool(tags={"app_instances", "resource_metrics_by_name", "resource_metrics_by_id"})
    async def edge_app_instance_resource_metrics( 
        identifier: str, 
        mtype: str,
        lookup_by: Literal["id", "name"] = "name", 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        create_plot: bool = False)-> dict[str, Any] | str:
        """
        Get the resource usage timeline of an edge application instance by name or ID.

        Get the resource usage timeline of an edge application instance as reported
        by the edge node where the edge application instance has been deployed.

        Args:
            identifier: The edge app instance ID or name to look up
            mtype: Metric type to retrieve (required). Valid values:
                   - UNSPECIFIED: Default/unspecified metric type
                   - CPU_TOTAL: Total CPU resources available
                   - CPU_USAGE: CPU utilization percentage
                   - MEMORY_TOTAL: Total memory available
                   - MEMORY_UTILIZATION: Memory utilization percentage
                   - NETWORK_TOTAL: Total network bandwidth/capacity
                   - NETWORK_RATES: Network throughput rates (in/out)
                   - EVENTS_COUNT: Number of events generated
                   - STORAGE_UTILIZATION: Storage space utilization
                   - STORAGE_IO_ZPOOL: ZFS pool I/O statistics
                   - STORAGE_IO_ZVOL: ZFS volume I/O statistics
            lookup_by: Search method - "id" for edge app instance ID lookup or "name" for name lookup (default: "name")
            start_time: Start time for metrics query in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
            end_time: End time for metrics query in ISO 8601 format (e.g., "2024-01-01T23:59:59Z")
            interval: Time interval/granularity for data points in ISO 8601 duration format (e.g., "PT1H" for 1 hour)
            create_plot: MAKE SURE to set to True, if user is asking for a plot. If True, wrap response with data and plot_instructions (plot generation instructions) for chart creation (default: False)

        Returns:
            MetricQueryResponse containing timeline data with timestamps and metric values
        """
         
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-metrics.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock metrics data for app instance: {identifier}, metric: {mtype}"
                )
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug(
            f"Invoked edge_app_instance_resource_metrics tool for app instance: {identifier}, metric: {mtype}, lookup_by: {lookup_by}"
        )

        # Validate required path parameters
        if not identifier or not identifier.strip():
            return "Error: identifier (app instance name or ID) is required and cannot be empty"

        if not mtype or not mtype.strip():
            return "Error: mType (metric type) is required and cannot be empty"

        # Define valid metric types
        valid_metric_types = [
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
        ]

        # Validate metric type
        if mtype not in valid_metric_types:
            return f"Error: Invalid mType '{mtype}'. Must be one of: {', '.join(valid_metric_types)}"

        # Validate datetime formats if provided
        if start_time:
            try:
                # Try to parse to validate format
                datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                return f"Error: Invalid start_time format '{start_time}'. Use ISO 8601 format (e.g., '2024-01-01T00:00:00Z')"

        if end_time:
            try:
                datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return f"Error: Invalid end_time format '{end_time}'. Use ISO 8601 format (e.g., '2024-01-01T23:59:59Z')"

        # Build query parameters
        query_params = []
        if start_time:
            query_params.append(f"startTime={urllib.parse.quote(start_time)}")
        if end_time:
            query_params.append(f"endTime={urllib.parse.quote(end_time)}")
        if interval:
            query_params.append(f"interval={urllib.parse.quote(interval)}")

        # Encode identifier for URL safety
        encoded_identifier = urllib.parse.quote(identifier, safe="")
        
        # Determine lookup method and build URL
        actual_lookup_method = lookup_by
        lookup_note = None
        
        # If looking up by ID but identifier is not a valid UUID, fallback to name lookup
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', falling back to name-based lookup")
            actual_lookup_method = "name"
            lookup_note = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found edge app instance by name instead. For future requests, use lookup_by='name' for this edge app instance."
        
        # Build URL based on determined lookup method
        lookup_endpoint = "id" if actual_lookup_method == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/{lookup_endpoint}/{encoded_identifier}/timeSeries/{mtype}"
        if query_params:
            url += "?" + "&".join(query_params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        
        logger.info(f"Getting resource metrics for app instance '{identifier}' (lookup_by: {actual_lookup_method}) with metric type '{mtype}'")
        
        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request for context
                result["_request_info"] = {
                    "app_instance_identifier": identifier,
                    "lookup_method": actual_lookup_method,
                    "metric_type": mtype,
                    "start_time": start_time,
                    "end_time": end_time,
                    "interval": interval,
                    "query_timestamp": datetime.now().isoformat()
                }

                # Add lookup note if we did a fallback
                if lookup_note:
                    result["_lookup_note"] = lookup_note

                # Add helpful summary if data points exist
                if isinstance(result, dict) and "data" in result:
                    data_points = result.get("data", [])
                    if data_points:
                        result["_summary"] = {
                            "total_data_points": len(data_points),
                            "time_range": {
                                "first": data_points[0].get("timestamp") if data_points else None,
                                "last": data_points[-1].get("timestamp") if data_points else None,
                            },
                        }
                
                # Wrap with plot instructions if requested and function is available
                if create_plot and create_plot_response_structure:
                    metric_context = f"Time-series metric data for {mtype} on app instance '{identifier}'. Default chart type is line. Use this guidance only if user requested a different chart type."
                    return create_plot_response_structure(result, metric_context)

                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"App instance with {actual_lookup_method} '{identifier}' not found or no metrics data available for metric type '{mtype}'"
                elif e.response.status_code == 403:
                    return f"Access denied: You don't have permission to access metrics for app instance '{identifier}'"
                elif e.response.status_code == 400:
                    return f"Bad request: Check your time parameters and metric type. Error: {e.response.text}"
                else:
                    return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"zedcloud", "edge_app_instances", "app_instances"})
    async def get_edge_app_instance_by_name(app_instance_name: str) -> str:
        """
        Get the configuration of an edge application instance by its name.

        Args:
            app_instance_name: User defined name of the app instance, unique across the enterprise

        Returns:
            JSON string containing the AppInstance configuration
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "edge-app-instances-detail.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                filtered_mock = filter_mock_by_identifier(
                    mock, app_instance_name, lookup_by="name", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"App instance with name '{app_instance_name}' not found."
                return json.dumps(filtered_mock, indent=2)

        token = await ensure_bearer_token()
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/name/{urllib.parse.quote(app_instance_name)}"

        logger.info(f"Fetching app instance configuration by name: {app_instance_name}")
        response = await make_zededa_request(url, "get", token)

        if response is None:
            return f"Failed to retrieve app instance with name: {app_instance_name}."

        # Check if error response (ZsrvResponse with error status)
        if (
            isinstance(response, dict)
            and "status" in response
            and response.get("status") != "SUCCESS"
        ):
            error_msg = response.get("error", {}).get("message", "Unknown error")
            return f"Error retrieving app instance: {error_msg}"

        # Handle case where API returns a list instead of a single object
        # This can happen with some ZedCloud API endpoints
        if isinstance(response, list):
            if len(response) == 0:
                return f"No app instance found with name: {app_instance_name}."
            # If multiple matches, take the first one (name should be unique per enterprise)
            if len(response) > 1:
                logger.warning(f"Multiple app instances found with name '{app_instance_name}', using first match")
            response = response[0]

        try:
            return json.dumps(response, indent=2)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize response to JSON: {e}")
            return f"Failed to serialize app instance configuration for name: {app_instance_name}."
