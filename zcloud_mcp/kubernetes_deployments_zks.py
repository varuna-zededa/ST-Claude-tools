"""
Zededa MCP tools for Kubernetes deployments management.

These tools provide agents with a comprehensive interface for querying, analyzing, and
managing Kubernetes deployments within Zededa's Kubernetes Service (ZKS) platform.

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


def register_kubernetes_deployment_tools(mcp):
    """Register all Kubernetes deployment-related MCP tools."""

    @mcp.tool(tags={"kubernetes", "deployments", "details"})
    async def get_kubernetes_deployment(deployment_id: str) -> dict[str, Any] | str:
        """
        Get detailed information about a specific Kubernetes deployment. Kubernetes
        deployments are sometimes referred to as installed Kubernetes applications.

        This tool retrieves comprehensive details about a deployment including its specification,
        current status, configuration, Helm chart data, target clusters, and metadata (creator,
        timestamps, etc.).

        Common Use Cases:
        - View complete deployment configuration and specifications
        - Understand Helm chart configuration and custom values
        - Check target cluster assignment for deployments
        - Review deployment history (created by, updated by, timestamps)
        - Analyze deployment resource requirements (replicas, ports, etc.)

        Args:
            deployment_id: Unique identifier of the deployment (e.g., "844cfe2b-2678-4fa7-8e13-5c25a78114cc")

        Returns:
            Dictionary containing:
            - id: Deployment unique identifier
            - name: Deployment name
            - title: Human-readable deployment title
            - description: Deployment description
            - type: Deployment type (HELMCHART, KUSTOMIZE, etc.)
            - spec: Complete deployment specification with Helm/Kustomize details
            - deployment_status: Current status (Ready, Pending, Failed, etc.)
            - created_at: Creation timestamp
            - updated_at: Last update timestamp
            - created_by: Creator email/username
            - updated_by: Last modifier email/username
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not deployment_id or not deployment_id.strip():
            return "Error: deployment_id is required and cannot be empty"

        # Encode deployment ID for URL safety
        encoded_id = urllib.parse.quote(deployment_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/deployments/id/{encoded_id}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(
            f"Retrieving Kubernetes deployment details for ID '{deployment_id}'"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "deployment_id": deployment_id,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving deployment: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Deployment with ID '{deployment_id}' not found. Check the deployment ID."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions to access this deployment."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid deployment ID format. Check the deployment ID."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve deployment details. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving deployment: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "deployments", "list"})
    async def list_kubernetes_deployments(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
    ) -> dict[str, Any] | str:
        """
        List all Kubernetes deployments with status summaries. Kubernetes deployments
        are sometimes referred to as installed Kubernetes applications.

        This tool provides a paginated view of all Kubernetes deployments in your infrastructure,
        including aggregated status statistics (ready, pending, failed counts) and key deployment
        information.

        Common Use Cases:
        - View all deployments and their current status
        - Get an overview of deployment health across the cluster
        - Find deployments by type (HelmChart, Kustomize, etc.)
        - Monitor deployment creation and update timestamps

        Args:
            page_size: Number of deployments per page (default: 20, max: 50)
            page_num: Page number to retrieve (starts at 1)

        Returns:
            Dictionary containing:
            - deployments: List of deployment objects with metadata
            - total_count: Total number of deployments
            - state_summary: Aggregated status counts (ready, pending, failed)
            - _guidance: Helpful message if results are truncated
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Enforce pagination limits
        effective_page_size = min(page_size or 20, 50)
        effective_page_num = max(page_num or 1, 1)

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/deployments?pageSize={effective_page_size}&pageNum={effective_page_num}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(
            f"Listing Kubernetes deployments (page {effective_page_num}, size {effective_page_size})"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata
                result["_request_info"] = {
                    "page_num": effective_page_num,
                    "page_size": effective_page_size,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving deployments: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return "Invalid request parameters. Check pagination values."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve deployments. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving deployments: {e}")
                return f"Unexpected error: {str(e)}"
