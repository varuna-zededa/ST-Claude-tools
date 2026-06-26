"""
Zededa MCP tools for ZKS cluster group management.

These tools provide agents with a comprehensive interface for querying cluster groups,
generating manifests, and monitoring cluster group status within Zededa's ZKS infrastructure.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional
import httpx
import urllib.parse
from datetime import datetime
from utils import (
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
)
from auth import ensure_bearer_token


def register_cluster_group_tools(mcp):
    """Register all cluster group-related MCP tools."""

    @mcp.tool(tags={"zks", "cluster", "groups", "manifest"})
    async def get_cluster_group_manifest(
        name: Optional[str] = None, project_name: Optional[str] = None
    ) -> dict[str, Any] | str:
        """
        Generate and retrieve a cluster group manifest.

        This tool generates a Kubernetes manifest based on cluster group configuration.
        Manifests can be filtered by cluster group name and project name.

        Common Use Cases:
        - Generate deployment manifests for cluster groups
        - Export cluster group configuration as YAML
        - Retrieve manifests for specific projects or cluster groups
        - Get cluster-ready manifests for GitOps workflows

        Args:
            name: Optional cluster group name filter
            project_name: Optional project name filter

        Returns:
            Dictionary containing:
            - manifest: Generated YAML manifest content
            - _request_info: Request metadata with filters applied
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/zks/cluster/groups/manifest"

        # Add optional query parameters
        params = []
        if name:
            params.append(f"name={urllib.parse.quote(name, safe='')}")
        if project_name:
            params.append(f"projectName={urllib.parse.quote(project_name, safe='')}")

        if params:
            url += "?" + "&".join(params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Generating cluster group manifest")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "query_time": datetime.now().isoformat(),
                }

                if name:
                    result["_request_info"]["cluster_group_name"] = name
                if project_name:
                    result["_request_info"]["project_name"] = project_name

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error generating manifest: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return (
                        "Invalid query parameters. Check name or project_name format."
                    )
                elif e.response.status_code == 404:
                    return "No cluster group found matching the specified criteria."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return (
                        "Server error. Failed to generate manifest. Please try again."
                    )
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error generating manifest: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"zks", "cluster", "groups", "status"})
    async def get_cluster_groups_status(
        group_id: Optional[str] = None,
        group_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """
        Get detailed status and resource information for cluster groups.

        This tool retrieves comprehensive status information including cluster readiness,
        resource summaries, deployment state, and per-cluster details for cluster groups.

        Common Use Cases:
        - Monitor cluster group deployment status
        - Check cluster readiness across groups
        - View resource health and readiness metrics
        - Get per-cluster status within a group
        - Filter cluster groups by ID, name, or project
        - Track resource reconciliation status

        Args:
            group_id: Optional filter by cluster group ID
            group_name: Optional filter by cluster group name
            project_name: Optional filter by project name

        Returns:
            Dictionary containing:
            - list: Cluster groups with state, readiness, resource summaries, and cluster details
            - _request_info: Request metadata with filters applied
            - _guidance: Pagination guidance if truncated
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/zks/cluster/groups/status"

        # Add optional query parameters
        params = []
        if group_id:
            params.append(f"id={urllib.parse.quote(group_id, safe='')}")
        if group_name:
            params.append(f"name={urllib.parse.quote(group_name, safe='')}")
        if project_name:
            params.append(f"projectName={urllib.parse.quote(project_name, safe='')}")

        if params:
            url += "?" + "&".join(params)

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Retrieving cluster groups status")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "query_time": datetime.now().isoformat(),
                }

                if group_id:
                    result["_request_info"]["group_id"] = group_id
                if group_name:
                    result["_request_info"]["group_name"] = group_name
                if project_name:
                    result["_request_info"]["project_name"] = project_name

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving cluster groups status: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return "Invalid filter parameters. Check group_id, group_name, or project_name."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve status. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving cluster groups status: {e}")
                return f"Unexpected error: {str(e)}"
