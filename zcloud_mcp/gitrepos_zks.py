"""
Zededa MCP tools for Git repository (GitRepo) management in Kubernetes.

These tools provide agents with a comprehensive interface for querying and analyzing
Git repository configurations and their sync status within Zededa's Kubernetes infrastructure.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any
import httpx
import urllib.parse
from datetime import datetime
from utils import (
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
)
from auth import ensure_bearer_token


def register_gitrepo_tools(mcp):
    """Register all Git repository-related MCP tools."""

    @mcp.tool(tags={"kubernetes", "gitops", "gitrepos", "details"})
    async def get_gitrepo(
        gitrepo_id: str,
    ) -> dict[str, Any] | str:
        """
        Get detailed information about a specific GitRepo configuration. Gitrepos are
        sometimes referred to as gitops repositories.

        This tool retrieves comprehensive details about a Git repository configuration,
        including its connection details, target cluster, sync status, conditions, and metadata.

        Common Use Cases:
        - View complete GitRepo configuration and repository details
        - Check Git URL, branch, and deployment paths
        - Monitor sync status and resource readiness
        - Review GitRepo history (creator, timestamps, recent updates)
        - Understand target cluster assignments

        Args:
            gitrepo_id: Unique identifier of the GitRepo (required).

        Returns:
            Dictionary containing:
            - id: GitRepo unique identifier
            - name: GitRepo name
            - title: Human-readable GitRepo title
            - description: GitRepo description
            - workspace: Target workspace
            - data: Repository configuration (url, branch, commit, paths, target)
            - status: Current status with display info, conditions, and resource counts
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
        if not gitrepo_id or not gitrepo_id.strip():
            return "Error: gitrepo_id is required and cannot be empty"

        # Encode gitrepo ID for URL safety
        encoded_id = urllib.parse.quote(gitrepo_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/gitrepos/id/{encoded_id}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving GitRepo configuration for ID '{gitrepo_id}'")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "gitrepo_id": gitrepo_id,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving GitRepo: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"GitRepo with ID '{gitrepo_id}' not found. Check the GitRepo ID."
                elif e.response.status_code == 403:
                    return (
                        "Access denied. Check your permissions to access this GitRepo."
                    )
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid GitRepo ID format. Check the GitRepo ID."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve GitRepo details. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving GitRepo: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "gitops", "gitrepos", "list"})
    async def list_gitrepos() -> dict[str, Any] | str:
        """
        List all GitRepo configurations with status summaries. Gitrepos are sometimes
        referred to as gitops repositories.

        This tool retrieves a comprehensive list of all Git repository configurations,
        including their current sync status, bundle deployment readiness, and aggregated
        status statistics.

        Common Use Cases:
        - View all GitRepo configurations and their sync status
        - Monitor GitOps deployment readiness across all repositories
        - Get overview of Active vs Pending repositories
        - Track repository statistics and state distribution

        Returns:
            Dictionary containing:
            - gitrepos: List of GitRepo configurations with id, name, title, status
            - totalCount: Total number of GitRepo configurations
            - stateSummary: Aggregated status counts (Active, Pending, etc.)
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/gitrepos"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Listing GitRepo configurations")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {"query_time": datetime.now().isoformat()}

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving GitRepos: {e}")
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
                    return "Server error. Failed to retrieve GitRepo list. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving GitRepos: {e}")
                return f"Unexpected error: {str(e)}"
