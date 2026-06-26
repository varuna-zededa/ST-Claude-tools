"""
Zededa MCP tools for ZKS (Zededa Kubernetes Service) instance management.

These tools provide agents with a comprehensive interface for querying and managing
Kubernetes cluster instances within Zededa's ZKS infrastructure.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Literal, Optional
import httpx
import urllib.parse
from datetime import datetime
from utils import (
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
)
from auth import ensure_bearer_token


def register_zks_instance_tools(mcp):
    """Register all ZKS instance-related MCP tools."""

    @mcp.tool(tags={"zks", "instances", "details"})
    async def get_zks_instance(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Get detailed information about a specific ZKS instance.

        This tool retrieves comprehensive details about a ZKS cluster instance,
        including its configuration, nodes, tags, and metadata.

        Common Use Cases:
        - View complete ZKS cluster configuration
        - Check cluster nodes and network interfaces
        - Review cluster metadata and tags
        - Verify cluster import status
        - Understand cluster architecture and capacity

        Args:
            identifier: ZKS instance ID or name. Example: 'production-cluster' or 'zks-instance-abc123'
            lookup_by: How to identify the instance - 'id' or 'name' (default: 'name')

        Returns:
            Dictionary containing:
            - id: Instance unique identifier
            - projectId: Associated project ID
            - name: Instance name
            - title: Human-readable instance title
            - description: Instance description
            - tags: Custom tags on the instance
            - nodes: List of nodes with id and cluster interface
            - isImported: Whether instance is imported
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not identifier or not identifier.strip():
            return "Error: identifier is required and cannot be empty"

        # Build URL based on lookup method
        if lookup_by == "id":
            encoded_id = urllib.parse.quote(identifier, safe="")
            url = f"{ZEDEDA_API_BASE}/api/v1/zks/instances/id/{encoded_id}"
        else:  # lookup_by == "name"
            encoded_name = urllib.parse.quote(identifier, safe="")
            url = f"{ZEDEDA_API_BASE}/api/v1/zks/instances/name/{encoded_name}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving ZKS instance {lookup_by} '{identifier}'")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "identifier": identifier,
                    "lookup_by": lookup_by,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving ZKS instance: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"ZKS instance with {lookup_by} '{identifier}' not found. Check the {lookup_by}."
                elif e.response.status_code == 403:
                    return (
                        "Access denied. Check your permissions to access this instance."
                    )
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid {lookup_by} format. Check the {lookup_by}."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve ZKS instance. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving ZKS instance: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"zks", "instances", "status"})
    async def get_zks_instances_status(
        zks_id: Optional[str] = None,
        zks_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """
        Get detailed status and capacity information for ZKS instances.

        This tool retrieves comprehensive status information including runtime metrics,
        resource capacity, node health, and deployment statistics for ZKS instances.

        Common Use Cases:
        - Monitor ZKS cluster capacity and resource usage
        - Check CPU and memory utilization
        - View pod capacity and usage
        - Get deployment count per cluster
        - Monitor cluster health status
        - Track online/offline nodes

        Args:
            zks_id: Optional filter by ZKS instance ID
            zks_name: Optional filter by ZKS instance name
            project_name: Optional filter by project name

        Returns:
            Dictionary containing:
            - list: Instances with status, capacity, resource metrics, deployment counts
            - summaries: Aggregated status counts (online, offline, suspect, etc.)
            - next: Pagination token for fetching more instances
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/zks/instances/status"

        # Add optional query parameters
        params = []
        if zks_id:
            params.append(f"zksid={urllib.parse.quote(zks_id, safe='')}")
        if zks_name:
            params.append(f"zksname={urllib.parse.quote(zks_name, safe='')}")
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

        logger.info("Retrieving ZKS instances status")

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

                if zks_id:
                    result["_request_info"]["zks_id"] = zks_id
                if zks_name:
                    result["_request_info"]["zks_name"] = zks_name
                if project_name:
                    result["_request_info"]["project_name"] = project_name
                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving ZKS status: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return "Invalid filter parameters. Check zks_id, zks_name, or project_name format."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve status. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving ZKS status: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"zks", "all_zks_instances", "list"})
    async def list_all_zks_instances() -> dict[str, Any] | str:
        """
        List all ZKS (Zededa Kubernetes Service) instances with basic information.

        This tool retrieves a list of all ZKS cluster instances, including their basic
        metadata, node count, and project association.

        Common Use Cases:
        - View all ZKS cluster instances
        - Get overview of Kubernetes clusters
        - Find clusters by name or project
        - Monitor cluster node counts
        - Discover available clusters for deployment

        Returns:
            Dictionary containing:
            - list: List of ZKS instances with id, name, title, project, node count, tags
            - next: Pagination token for fetching more instances
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/zks/instances"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Listing ZKS instances")

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

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving ZKS instances: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return "Invalid request parameters."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve ZKS instances. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving ZKS instances: {e}")
                return f"Unexpected error: {str(e)}"
