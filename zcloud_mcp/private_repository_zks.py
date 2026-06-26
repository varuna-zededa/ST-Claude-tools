"""
Zededa MCP tools for private Helm repository management.

These tools provide agents with a comprehensive interface for querying and analyzing
private Helm repositories configured within Zededa's Kubernetes infrastructure.

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


def register_private_repository_tools(mcp):
    """Register all private Helm repository-related MCP tools."""

    @mcp.tool(tags={"kubernetes", "private_helm_repository", "details"})
    async def get_private_helm_repository(
        private_repo_id: str,
    ) -> dict[str, Any] | str:
        """
        Get detailed information about a specific private Helm repository.

        This tool retrieves comprehensive details about a private Helm repository configuration,
        including its metadata, repository details, authentication configuration, and status.

        Common Use Cases:
        - View complete repository configuration and URL
        - Check authentication type and credentials
        - Verify repository accessibility and status
        - Review repository metadata and tags
        - Check repository type (HELM_INDEX, GIT, etc.)

        Args:
            private_repo_id: Unique identifier of the private repository (required). Example: 'private-repo-abc123'

        Returns:
            Dictionary containing:
            - id: Repository unique identifier
            - metadata: Name, title, description, and tags
            - spec: Repository details (type, URL, branch), authentication config
            - status: Accessibility status and error information
            - repoIdentifier: Repository identifier string
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not private_repo_id or not private_repo_id.strip():
            return "Error: private_repo_id is required and cannot be empty"

        # Encode private repo ID for URL safety
        encoded_id = urllib.parse.quote(private_repo_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/helm/repository/id/{encoded_id}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(
            f"Retrieving private Helm repository configuration for ID '{private_repo_id}'"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "private_repo_id": private_repo_id,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving private repository: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Private Helm repository with ID '{private_repo_id}' not found. Check the repository ID."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions to access this repository."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid repository ID format. Check the repository ID."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve repository details. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving private repository: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "helm_charts", "private_repo"})
    async def get_private_repository_charts(
        private_repo_id: str,
    ) -> dict[str, Any] | str:
        """
        Get Helm charts available in a specific private repository.

        This tool retrieves a list of all available Helm charts from a private repository,
        including all chart versions, metadata, descriptions, and download URLs.

        Common Use Cases:
        - Discover charts available in a private repository
        - View all versions of specific charts
        - Get chart metadata (app version, creation date, digest)
        - Find charts by name or keyword
        - Browse available private charts for deployment

        Args:
            private_repo_id: Unique identifier of the private repository (required). Example: 'private-repo-abc123'

        Returns:
            Dictionary containing:
            - api_version: Helm chart API version
            - repo_identifier: Repository identifier
            - repo_name: Human-readable repository name
            - generated: Timestamp when the chart list was generated
            - entries: Dictionary mapping chart names to lists of versions
              Each entry contains: name, version, app_version, description, created, digest, urls
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not private_repo_id or not private_repo_id.strip():
            return "Error: private_repo_id is required and cannot be empty"

        # Encode private repo ID for URL safety
        encoded_id = urllib.parse.quote(private_repo_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/helm/repository/id/{encoded_id}/charts"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Retrieving charts from private repository '{private_repo_id}'")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "private_repo_id": private_repo_id,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving repository charts: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Private repository with ID '{private_repo_id}' not found. Check the repository ID."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions to access this repository."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid repository ID format. Check the repository ID."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve repository charts. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving repository charts: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "private_helm_repository", "list_all"})
    async def list_all_private_helm_repositories() -> dict[str, Any] | str:
        """
        List all private Helm repositories with status information.

        This tool retrieves a comprehensive list of all configured private Helm repositories,
        including their metadata, configuration type, accessibility status, and repository identifiers.

        Common Use Cases:
        - View all configured private Helm repositories
        - Check repository accessibility status
        - Find repositories by type (Helm Index, Git, etc.)
        - Monitor repository connection health
        - Discover available private chart sources

        Returns:
            Dictionary containing:
            - list: List of private repository configurations with metadata, spec, and status
            - total: Total number of private repositories
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/helm/repository"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Listing private Helm repositories")

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
                logger.error(f"Network error retrieving private repositories: {e}")
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
                    return "Server error. Failed to retrieve private repositories. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving private repositories: {e}")
                return f"Unexpected error: {str(e)}"
