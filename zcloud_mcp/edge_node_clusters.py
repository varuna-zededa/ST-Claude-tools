"""
Zededa MCP tools for Edge-Node Cluster Service.
"""
from typing import Any, Literal, Optional
import urllib.parse
from utility.field_extractors import EdgeNodeClusterFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, is_valid_uuid, logger
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_edge_node_cluster_tools(mcp):
    """Register all edge-node cluster-related MCP tools (GET methods only)."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"edge_node_cluster", "clusters"})
    async def query_edge_node_clusters(
            filter_project_name: Optional[str] = None,
            filter_project_name_pattern: Optional[str] = None,
            filter_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query edge-node clusters from Zededa with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            filter_project_name: Filter by project name
            filter_project_name_pattern: Filter by project name pattern (supports wildcards)
            filter_name_pattern: Filter by cluster name pattern (supports wildcards)
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of edge-node clusters with requested fields
        """
        # Use the pre-configured EdgeNodeClusterFieldExtractor
        field_extractor = EdgeNodeClusterFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/cluster"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    filter_project_name=filter_project_name,
                    filter_project_name_pattern=filter_project_name_pattern,
                    filter_name_pattern=filter_name_pattern,
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

        if filter_project_name:
            params["filter.projectName"] = filter_project_name
        if filter_project_name_pattern:
            params["filter.projectNamePattern"] = filter_project_name_pattern
        if filter_name_pattern:
            params["filter.namePattern"] = filter_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster"
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
            return "Failed to retrieve edge-node clusters."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"edge_node_cluster", "cluster", "available_projects_for_edge_node_cluster"})
    async def get_edge_node_cluster_available_projects(
            filter_project_name: Optional[str] = None,
            filter_project_name_pattern: Optional[str] = None,
            filter_name_pattern: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Get the list of available projects for edge-node clusters.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            filter_project_name: Filter by project name
            filter_project_name_pattern: Filter by project name pattern (supports wildcards)
            filter_name_pattern: Filter by name pattern (supports wildcards)
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of available projects with requested fields
        """
        # Use the pre-configured EdgeNodeClusterFieldExtractor (reusing for project list)
        field_extractor = EdgeNodeClusterFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/cluster/available/projects"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    filter_project_name=filter_project_name,
                    filter_project_name_pattern=filter_project_name_pattern,
                    filter_name_pattern=filter_name_pattern,
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

        if filter_project_name:
            params["filter.projectName"] = filter_project_name
        if filter_project_name_pattern:
            params["filter.projectNamePattern"] = filter_project_name_pattern
        if filter_name_pattern:
            params["filter.namePattern"] = filter_name_pattern
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/available/projects"
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
            return "Failed to retrieve available projects for edge-node clusters."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
    
    @mcp.tool(tags={"edge_node_cluster", "cluster", "by_name", "by_id"})
    async def get_edge_node_cluster(
            identifier: str, lookup_by: Literal["id", "name"] = "name") -> dict[str, Any] | str:
        """Get a specific edge-node cluster by its name.
            Args:
                identifier: The edge node cluster ID or name to look up
                lookup_by: Search method - "id" for edge node cluster ID lookup or "name" for name lookup (default: "name")
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"edge-node-clusters-detail.json")
            if mock is not None:
                # Use intelligent filtering with explicit ID lookup
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Failed to retrieve edge-node cluster with ID: {id}."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token  

         # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup")
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/name/{urllib.parse.quote(identifier)}"
            response = await make_zededa_request(url, "get", token)
            if response is not None:
                # Success with name lookup - inform the LLM
                response["_lookup_note"] = f"Note: '{identifier}' was provided as an ID but is not a valid UUID. Successfully found edge node cluster by name instead. For future requests, use lookup_by='name' for this edge node cluster."
                return response
            # If name lookup also fails, return error
            return f"Invalid edge node cluster ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but edge node cluster not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        if lookup_endpoint == "name":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/name/{urllib.parse.quote(identifier)}"
        elif lookup_endpoint == "id":
            url = f"{ZEDEDA_API_BASE}/api/v1/cluster/id/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"edge node cluster not found. Check that the {lookup_by} '{identifier}' is correct."
        return response 

    @mcp.tool(tags={"edge_node_cluster", "cluster", "ports"})
    async def get_edge_node_cluster_ports(
            id: str) -> dict[str, Any] | str:
        """Get the list of interface ports for an edge-node cluster."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node cluster with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/id/{id}/ports"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve interface ports for edge-node cluster with ID: {id}."
        return response

    @mcp.tool(tags={"edge_node_cluster", "cluster", "raw_status"})
    async def get_edge_node_cluster_raw_status(
            id: str) -> dict[str, Any] | str:
        """Get the raw (unprocessed) status of an edge-node cluster as reported by the cluster reporter."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node cluster with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/id/{id}/raw/status"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve raw status for edge-node cluster with ID: {id}."
        return response

    @mcp.tool(tags={"edge_node_cluster", "cluster", "status_from_cluster_reporter"})
    async def get_edge_node_cluster_status(
            id: str) -> dict[str, Any] | str:
        """Get the status of an edge-node cluster as reported by the cluster reporter."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node cluster with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/id/{id}/status"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve status for edge-node cluster with ID: {id}."
        return response

    @mcp.tool(tags={"edge_node_cluster", "cluster", "upgrade", "status", "from_cluster_reporter"})
    async def get_edge_node_cluster_upgrade_status(
            id: str) -> dict[str, Any] | str:
        """Get the eve-os upgrade status of an edge-node cluster as reported by the cluster reporter."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node cluster with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/id/{id}/upgrade/status"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve upgrade status for edge-node cluster with ID: {id}."
        return response

    @mcp.tool(tags={"edge-node", "cluster", "node_id"})
    async def get_edge_node_cluster_by_node_id(
            id: str) -> dict[str, Any] | str:
        """Get the configuration of an edge-node cluster by node ID."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("edge-node-clusters-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                # Use intelligent filtering by ID
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Edge node cluster with node ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/node/id/{id}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve edge-node cluster with node ID: {id}."
        return response
