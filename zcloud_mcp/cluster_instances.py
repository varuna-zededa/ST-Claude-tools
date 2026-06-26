"""
Zededa MCP tools for Orchestrator Service - Cluster Instances.
"""
from typing import Any, Literal, Optional
import urllib.parse
from utility.field_extractors import ClusterInstanceFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, is_valid_uuid, logger
from auth import ensure_bearer_token


def register_cluster_instance_tools(mcp):
    """Register all cluster instance-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"get_all_cluster_instances", "from_orchestrator"})
    async def query_all_cluster_instances_from_orchestrator(
            summary: Optional[bool] = None,
            project: Optional[str] = None,
            name_pattern: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            cluster_type: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query cluster instances from Orchestrator Service with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Return summary information only
            project: Filter by project
            name_pattern: Filter by name pattern (supports wildcards)
            project_name_pattern: Filter by project name pattern (supports wildcards)
            cluster_type: Filter by cluster type
            page_token: Page token for pagination
            order_by: Fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of cluster instances with requested fields
        """
        # Use the pre-configured ClusterInstanceFieldExtractor
        field_extractor = ClusterInstanceFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/cluster/instances"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("cluster-instances-list.json",
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

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if project:
            params["project"] = project
        if name_pattern:
            params["namePattern"] = name_pattern
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
        if cluster_type:
            params["clusterType"] = cluster_type
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
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances"
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
            return "Failed to retrieve cluster instances."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
    @mcp.tool(tags={"cluster_instance_by_id", "cluster_instance_by_name", "from_orchestrator", })
    async def get_cluster_instance_from_orchestrator(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    )  -> dict[str, Any] | str:
        """Get a specific cluster instance from Orchestrator Service by its ID or name.
            Args:
                identifier: The cluster instance ID or name to look up
                lookup_by: Search method - "id" for cluster instance ID lookup or "name" for name lookup (default: "name")"""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"cluster-instances-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found cluster instance by name instead. For future requests, use lookup_by='name' for this cluster instance."
                return response
            # If name lookup also fails, return error
            return f"Invalid cluster instance ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but cluster instance not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/id/{identifier}"
        elif lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"cluster instance not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
 
    @mcp.tool(tags={"cluster_instance_status_by_id", "cluster_instance_status_by_name","from_orchestrator"})
    async def get_cluster_instance_status_from_orchestrator( 
        identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get the status of a cluster instance from the Orchestrator Service by its ID or name.
            Args:
                identifier: The cluster instance status ID or name to look up
                lookup_by: Search method - "id" for cluster instance status ID lookup or "name" for name lookup (default: "name")"""

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"cluster-instances-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found cluster instance status by name instead. For future requests, use lookup_by='name' for this cluster instance."
                return response
            # If name lookup also fails, return error
            return f"Invalid cluster instance status ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but cluster instance status not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/id/{identifier}/status"
        elif lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"cluster instance not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"cluster_instance_kubeconfig_by_id", "cluster_instance_kubeconfig_by_name", "from_orchestrator"})
    async def get_cluster_instance_kubeconfig_from_orchestrator(
        identifier: str, lookup_by: Literal["id", "name"] = "name")-> dict[str, Any] | str:
        """Get the kubeconfig of a cluster instance from Orchestrator Service by its ID or name.
            Args:
                identifier: The cluster instance kubeconfig ID or name to look up
                lookup_by: Search method - "id" for cluster instance kubeconfig ID lookup or "name" for name lookup (default: "name")"""

        # Validate UUID if looking up by id - if invalid, try as name instead
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"cluster-instances-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
    
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status/kubeconfig"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found cluster instance kubeconfig by name instead. For future requests, use lookup_by='name' for this cluster instance."
                return response
            # If name lookup also fails, return error
            return f"Invalid cluster instance kubeconfig ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but cluster instance kubeconfig not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/id/{identifier}/status/kubeconfig"
        elif lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status/kubeconfig"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"cluster instance not found. Check that the {lookup_by} '{identifier}' is correct."
        return response 

    @mcp.tool(tags={"cluster_instance_kubeconfig_by_id","cluster_instance_kubeconfig_by_name", "from_orchestrator"})
    async def download_cluster_instance_kubeconfig_from_orchestrator(
        identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Download the status kubeconfig of a cluster instance from Orchestrator Service by its ID or Name.
            Args:
                identifier: The cluster instance kubeconfig download ID or name to look up
                lookup_by: Search method - "id" for cluster instance kubeconfig download ID lookup or "name" for name lookup (default: "name")"""


        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"cluster-instances-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status/kubeconfig/download"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found cluster instance kubeconfig by name download instead. For future requests, use lookup_by='name' for this cluster instance."
                return response
            # If name lookup also fails, return error
            return f"Invalid cluster instance kubeconfig download ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but cluster instance kubeconfig download not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "id":
             url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/id/{identifier}/status/kubeconfig/download"
        elif lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/status/kubeconfig/download"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"cluster instance kubeconfig download not found. Check that the {lookup_by} '{identifier}' is correct."
        return response 
        

    @mcp.tool(tags={"cluster_instances_event_by_id", "cluster_instances_event_by_name", "from_orchestrator"})
    async def get_cluster_instance_events_from_orchestrator(
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
        total_pages: Optional[int] = None, 
    ) -> dict[str, Any] | str:
        """Get cluster instance events from Orchestrator Service by its ID or name.
            Args:
                identifier: The cluster instance events ID or name to look up
                lookup_by: Search method - "id" for cluster instance events ID lookup or "name" for name lookup (default: "name")
                start_time: Start time in ISO 8601 format (e.g., "2024-01-01T00:00:00Z")
                end_time: End time in ISO 8601 format (e.g., "2024-01-01T23:59:59Z")
        """
        

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"cluster-instances-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token
        
        params = {}

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

        params_url = ""
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
            params_url += "?" + "&".join(query_parts)

        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/events"
            if params_url:
                url += params_url
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found cluster instance kubeconfig by name download instead. For future requests, use lookup_by='name' for this cluster instance."
                return response
            # If name lookup also fails, return error
            return f"Invalid cluster instance kubeconfig download ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but cluster instance kubeconfig download not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/id/{identifier}/events"
            if params_url:
                url += params_url
        elif lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/name/{urllib.parse.quote(identifier)}/events"
            if params_url:
                url += params_url
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"cluster instance kubeconfig download not found. Check that the {lookup_by} '{identifier}' is correct."
        return response 
        
    @mcp.tool(tags={"all_cluster_instances_status", "from_orchestrator"})
    async def query_all_cluster_instance_status_from_orchestrator(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            project: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query cluster instance status from Orchestrator Service with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Return summary information only
            name_pattern: Filter by name pattern (supports wildcards)
            project: Filter by project
            project_name_pattern: Filter by project name pattern (supports wildcards)
            page_token: Page token for pagination
            order_by: Fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of cluster instance statuses with requested fields
        """
        # Use the pre-configured ClusterInstanceFieldExtractor
        field_extractor = ClusterInstanceFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/cluster/instances/status"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("cluster-instances-list.json",
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

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if project:
            params["project"] = project
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
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

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/status"
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
            return "Failed to retrieve cluster instance status."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"cluster_instances_status_and_config", "from_orchestrator"})
    async def query_orchestrator_cluster_instance_status_and_config(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            project: Optional[str] = None,
            project_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query cluster instance status and config from Orchestrator Service with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Return summary information only
            name_pattern: Filter by name pattern (supports wildcards)
            project: Filter by project
            project_name_pattern: Filter by project name pattern (supports wildcards)
            page_token: Page token for pagination
            order_by: Fields to order by
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of cluster instance status configs with requested fields
        """
        # Use the pre-configured ClusterInstanceFieldExtractor
        field_extractor = ClusterInstanceFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/cluster/instances/status-config"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("cluster-instances-list.json",
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

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if project:
            params["project"] = project
        if project_name_pattern:
            params["projectNamePattern"] = project_name_pattern
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

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/status-config"
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
            return "Failed to retrieve cluster instance status and config."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"cluster_instances_tags", "from_orchestrator"})
    async def query_orchestrator_cluster_instance_tags(
            page_token: Optional[str] = None,
            order_by: Optional[list[str]] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """Query cluster instance tags from Orchestrator Service."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("cluster-instances-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

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

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/tags"
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
            return "Failed to retrieve cluster instance tags."
        return response
