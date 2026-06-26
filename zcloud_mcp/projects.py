"""
Zededa MCP tools for project management.

These tools provide agents with a comprehensive interface for querying, monitoring, and
analyzing project information, status, events, and metrics from Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
from utility.field_extractors import ProjectFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    make_zededa_request,
    is_valid_uuid,
    ZEDEDA_API_BASE,
    logger,
    load_mock_json,
)
from mock_utils import filter_mock_list, select_mock_fields, filter_mock_by_identifier
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


def register_project_tools(mcp):
    """Register all project-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Project tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"all_projects"})
    async def get_all_projects(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Get all projects from Zedcloud.
        
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
            Dictionary containing list of projects with metadata, or error message string
        """
        # Use the pre-configured ProjectFieldExtractor
        field_extractor = ProjectFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/projects"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-list.json", required=USE_MOCK_API_MCP_DATA)
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
        if isinstance(token, str) and "Authorization header" in token:
            return token
            
        url = f"{ZEDEDA_API_BASE}/api/v1/projects?next.pageSize={effective_page_size}&next.pageNum={page_num}"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return "Failed to retrieve projects."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"project", "lookup by id or name"})
    async def get_project(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific project.

        Use this tool when you need to get complete configuration and metadata for a project.
        The tool automatically resolves the project from either its unique ID or human-readable name.

        Args:
            identifier: The project ID or name to look up
            lookup_by: Search method - "id" for project ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing project details including ID, name, title, description,
            type, and configuration. Returns error message if project not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-detail.json")
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
                    return f"Project not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/projects/name/{identifier}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found project by name instead. For future requests, use lookup_by='name' for this project."
                return response
            # If name lookup also fails, return error
            return f"Invalid project ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but project not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/{lookup_endpoint}/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Project not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"all_projects_status", "status", "config", "summary", "plot", "visualization"})
    async def get_project_status_config_summary(
            create_plot: bool = False) -> dict[str, Any] | str:
        """
        Get project status and configuration summary across all projects.

        This tool provides aggregated status and configuration information for all projects,
        optimized for visualization and analysis.

        Args:
            create_plot: If True, wrap response with data and plot_instructions for chart creation (default: False)

        Returns:
            Dictionary containing aggregated project status and config data suitable for visualization
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-status-config-summary.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/projects/status-config?summary=true"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return "Failed to retrieve project status-config summary."
        
        logger.debug("Retrieved project status-config summary")
        
        # Wrap with plot instructions if requested and function is available
        if create_plot and create_plot_response_structure:
            logger.debug("Creating plot instructions for project status-config summary")
            metric_context = "Project status and configuration summary across all resource groups. Default chart type is bar or pie chart showing distribution of project states."
            return create_plot_response_structure(response, metric_context)
        
        return response

    @mcp.tool(tags={"projects", "status"})
    async def query_project_status(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            status: Optional[int] = None,
            type: Optional[str] = None,
            tags: Optional[str] = None,
            page_size: Optional[int] = 20,
            page_num: Optional[int] = 1,
            order_by: Optional[str] = None,
            fields: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query the status of projects.
        
        This tool provides comprehensive filtering and pagination options to query 
        project status information from the ZedCloud platform.
        
        Args:
            summary: Return summary information only (boolean)
            name_pattern: Filter by project name pattern (supports wildcards)
            status: Filter by project status (integer)
            type: Filter by project type. Valid values:
                  TAG_TYPE_UNSPECIFIED, TAG_TYPE_GENERIC, TAG_TYPE_PROJECT, 
                  TAG_TYPE_AZURE, TAG_TYPE_DEPLOYMENT
            tags: Filter by project tags (JSON stringified key-value pairs)
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            order_by: Field to order results by
            fields: Specific fields to return: id, name, status (comma-separated)
                   IMPORTANT: Only use this parameter if you want all other data to be filtered.
                   
        Returns:
            Dictionary containing filtered project status records with metadata
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-status.json")
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    name_pattern=name_pattern,
                    status=status,
                    type=type,
                    tags=tags,
                )
                # Apply field selection if specified
                if fields and filtered_mock:
                    filtered_mock = select_mock_fields(filtered_mock, fields.split(','))
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Build query parameters
        params = []
        effective_page_size = min(page_size or 20, 50)
        params.append(f"next.pageSize={effective_page_size}")
        params.append(f"next.pageNum={page_num}")
        
        if summary is not None:
            params.append(f"summary={str(summary).lower()}")
        if name_pattern:
            params.append(f"namePattern={name_pattern}")
        if status is not None:
            params.append(f"status={status}")
        if type:
            params.append(f"type={type}")
        if tags:
            params.append(f"tags={tags}")
        if order_by:
            params.append(f"next.orderBy={order_by}")
        if fields:
            params.append(f"fields={fields}")
        
        query_string = "&".join(params)
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/status?{query_string}"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return "Failed to retrieve projects status."

        return response

    @mcp.tool(tags={"projects", "status", "config"})
    async def query_project_status_config(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            status: Optional[int] = None,
            type: Optional[str] = None,
            tags: Optional[str] = None,
            page_size: Optional[int] = 20,
            page_num: Optional[int] = 1,
            order_by: Optional[str] = None,
            fields: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query the status and configuration of projects.
        
        This tool provides comprehensive filtering and pagination options to query 
        both status and configuration information from the ZedCloud platform.
        
        Args:
            summary: Return summary information only (boolean)
            name_pattern: Filter by project name pattern (supports wildcards)
            status: Filter by project status (integer)
            type: Filter by project type. Valid values:
                  TAG_TYPE_UNSPECIFIED, TAG_TYPE_GENERIC, TAG_TYPE_PROJECT, 
                  TAG_TYPE_AZURE, TAG_TYPE_DEPLOYMENT
            tags: Filter by project tags (JSON stringified key-value pairs)
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            order_by: Field to order results by
            fields: Specific fields to return: id, name, status (comma-separated)
                   IMPORTANT: Only use this parameter if you want all other data to be filtered.
                   
        Returns:
            Dictionary containing filtered project status and config records with metadata
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-status-config.json")
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    name_pattern=name_pattern,
                    status=status,
                    type=type,
                    tags=tags,
                )
                # Apply field selection if specified
                if fields and filtered_mock:
                    filtered_mock = select_mock_fields(filtered_mock, fields.split(','))
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Build query parameters
        params = []
        effective_page_size = min(page_size or 20, 50)
        params.append(f"next.pageSize={effective_page_size}")
        params.append(f"next.pageNum={page_num}")
        
        if summary is not None:
            params.append(f"summary={str(summary).lower()}")
        if name_pattern:
            params.append(f"namePattern={name_pattern}")
        if status is not None:
            params.append(f"status={status}")
        if type:
            params.append(f"type={type}")
        if tags:
            params.append(f"tags={tags}")
        if order_by:
            params.append(f"next.orderBy={order_by}")
        if fields:
            params.append(f"fields={fields}")
        
        query_string = "&".join(params)
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/status-config?{query_string}"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return "Failed to retrieve projects status-config."
        return response

    @mcp.tool(tags={"projects", "tags"})
    async def get_project_tags(
            obj_id: Optional[str] = None,
            obj_name: Optional[str] = None,
            page_size: Optional[int] = 20,
            page_num: Optional[int] = 1,
            order_by: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query project tag key-values.
        
        Get tag information associated with projects/. Tags are metadata
        key-value pairs that can be used for organization and filtering.
        
        Args:
            obj_id: Object ID which tags are associated with
            obj_name: Object name which tags are associated with
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            order_by: Field to order results by
            
        Returns:
            Dictionary containing tag records with key-value pairs and metadata
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-tags.json")
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    obj_id=obj_id,
                    obj_name=obj_name,
                )
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Build query parameters
        params = []
        effective_page_size = min(page_size or 20, 50)
        params.append(f"next.pageSize={effective_page_size}")
        params.append(f"next.pageNum={page_num}")
        
        if obj_id:
            params.append(f"filter.objId={obj_id}")
        if obj_name:
            params.append(f"filter.objName={obj_name}")
        if order_by:
            params.append(f"next.orderBy={order_by}")
        
        query_string = "&".join(params)
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/tags?{query_string}"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return "Failed to retrieve projects tags."

        return response

    @mcp.tool(tags={"project", "status"})
    async def get_project_status(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Get project status (without security details).
        
        Retrieve the status information for a specific project by ID or name.
        
        Args:
            identifier: The project ID or name to look up
            lookup_by: Search method - "id" for project ID or "name" for name (default: "name")
            
        Returns:
            Dictionary containing project status information, or error message if not found
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-status-by-name.json")
            if mock is not None:
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Project with {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
            
        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/{lookup_endpoint}/{identifier}/status"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return f"Failed to retrieve project status for {lookup_by}: {identifier}."
        
        return response

    @mcp.tool(tags={"project", "events"})
    async def get_project_events(
            identifier: str,
            lookup_by: Literal["id", "name"] = "name",
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            resource: Optional[str] = None,
            page_size: Optional[int] = 20,
            page_num: Optional[int] = 1) -> dict[str, Any] | str:
        """
        Get configuration and status events for a project.
        
        Retrieve event history for a specific project, with optional filtering by time range,
        severity, and resource type.
        
        Args:
            identifier: The project ID or name to look up
            lookup_by: Search method - "id" for project ID or "name" for name (default: "name")
            start_time: Start time for event filtering (ISO 8601 format)
            end_time: End time for event filtering (ISO 8601 format)
            resource: Filter by resource type
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            
        Returns:
            Dictionary containing filtered event records with metadata
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-events-by-name.json")
            if mock is not None:
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Project events for {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Build query parameters
        params = []
        effective_page_size = min(page_size or 20, 50)
        params.append(f"next.pageSize={effective_page_size}")
        params.append(f"next.pageNum={page_num}")
        
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")
        if resource:
            params.append(f"resource={resource}")
        query_string = "&".join(params)
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/{lookup_endpoint}/{identifier}/events?{query_string}"
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return f"Failed to retrieve project events for {lookup_by}: {identifier}."

        return response

    @mcp.tool(tags={"project", "metrics", "timeseries", "monitoring", "plot", "visualization"})
    async def get_project_metrics(
            identifier: str,
            metric_type: str,
            lookup_by: Literal["id", "name"] = "name",
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            interval: Optional[str] = None,
            create_plot: bool = False) -> dict[str, Any] | str:
        """
        Get resource usage timeline (metrics) for a project.
        
        Retrieve time-series metrics data for a specific project as reported by the edge nodes
        in the project. Supports various metric types for monitoring resource utilization.
        
        Args:
            identifier: The project ID or name to look up
            metric_type: Type of metric to retrieve. Valid values:
                        UNSPECIFIED, CPU_TOTAL, CPU_USAGE, MEMORY_TOTAL, MEMORY_UTILIZATION,
                        NETWORK_TOTAL, NETWORK_RATES, EVENTS_COUNT, STORAGE_UTILIZATION,
                        STORAGE_IO_ZPOOL, STORAGE_IO_ZVOL
            lookup_by: Search method - "id" for project ID or "name" for name (default: "name")
            start_time: Start time for metrics (ISO 8601 format)
            end_time: End time for metrics (ISO 8601 format)
            interval: Time interval for data points (ISO 8601 duration format, e.g., "PT1H" for 1 hour)
            create_plot: If True, wrap response with data and plot_instructions for chart creation (default: False)
            
        Returns:
            Dictionary containing time-series metrics data with timestamps and values
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("projects-metrics-by-name.json")
            if mock is not None:
                # Use intelligent filtering by ID or name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Project metrics for {lookup_by} '{identifier}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Build query parameters
        params = []
        if start_time:
            params.append(f"startTime={start_time}")
        if end_time:
            params.append(f"endTime={end_time}")
        if interval:
            params.append(f"interval={interval}")
        
        query_string = "&".join(params) if params else ""
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/projects/{lookup_endpoint}/{identifier}/timeSeries/{metric_type}"
        if query_string:
            url += f"?{query_string}"
        
        response = await make_zededa_request(url, "get", token)
        
        if response is None:
            return f"Failed to retrieve project metrics for {lookup_by}: {identifier}."
        
        # Wrap with plot instructions if requested and function is available
        if create_plot and create_plot_response_structure:
            logger.debug("Creating plot instructions for project metrics")
            metric_context = f"Time-series metric data for {metric_type} on project '{identifier}'. Default chart type is line chart showing resource usage over time."
            return create_plot_response_structure(response, metric_context)
        
        return response
