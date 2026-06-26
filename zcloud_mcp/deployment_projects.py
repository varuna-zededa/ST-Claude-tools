"""
Zededa MCP tools for deployment project management.

These tools provide agents with a comprehensive interface for querying and monitoring
deployment projects and their configurations from Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional
import urllib.parse
from utility.field_extractors import DeploymentProjectFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    make_zededa_request,
    is_valid_uuid,
    ZEDEDA_API_BASE,
    logger,
    load_mock_json,
)
from auth import ensure_bearer_token


def register_deployment_project_tools(mcp):
    """Register all deployment project-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Deployment project tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"all_deployments_in_projects", "deployments in projects"})
    async def get_project_deployments(
            project_id: str,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Get all deployments within a project.

        This tool retrieves the list of all deployments for a specific project using the v2 API.
        Useful for understanding what deployments are configured within a project.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            project_id: Project identifier (UUID format required)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of deployments with their configurations and metadata,
            or error message string if the request fails
        """
        # Use the pre-configured DeploymentProjectFieldExtractor
        field_extractor = DeploymentProjectFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v2/projects/id/{project_id}/deployments"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("deployment-projects-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not project_id or not project_id.strip():
            return "Error: project_id parameter is required and cannot be empty"

        # Validate UUID format
        if not is_valid_uuid(project_id):
            return f"Invalid project_id format (not a UUID): '{project_id}'. Please provide a valid project UUID."

        # Build URL
        encoded_project_id = urllib.parse.quote(project_id, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v2/projects/id/{encoded_project_id}/deployments"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve deployments for project ID: {project_id}"

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"deployment project"})
    async def get_project_deployment(
            project_id: str, deployment_id: str) -> dict[str, Any] | str:
        """
        Get detailed information about a specific deployment within a project.

        This tool retrieves comprehensive deployment status and configuration details
        for a specific deployment ID within a project using the v2 API.

        Args:
            project_id: Project identifier (UUID format required)
            deployment_id: Deployment identifier (UUID format required)

        Returns:
            Dictionary containing deployment details including status, configuration,
            and associated resources. Returns error message string if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("deployment-projects-detail.json")
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameters
        if not project_id or not project_id.strip():
            return "Error: project_id parameter is required and cannot be empty"

        if not deployment_id or not deployment_id.strip():
            return "Error: deployment_id parameter is required and cannot be empty"

        # Validate UUID formats
        if not is_valid_uuid(project_id):
            return f"Invalid project_id format (not a UUID): '{project_id}'. Please provide a valid project UUID."

        if not is_valid_uuid(deployment_id):
            return f"Invalid deployment_id format (not a UUID): '{deployment_id}'. Please provide a valid deployment UUID."

        # Build URL
        encoded_project_id = urllib.parse.quote(project_id, safe='')
        encoded_deployment_id = urllib.parse.quote(deployment_id, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v2/projects/id/{encoded_project_id}/deployments/id/{encoded_deployment_id}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve deployment with ID '{deployment_id}' in project '{project_id}'"

        return response
