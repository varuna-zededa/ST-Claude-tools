"""
Zededa MCP tools for Helm chart management.

These tools provide agents with a comprehensive interface for querying and analyzing
Helm charts available in Kubernetes repositories within Zededa's infrastructure.

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
from utils import ZEDEDA_API_BASE, USER_AGENT, logger
from auth import ensure_bearer_token


def register_helm_chart_tools(mcp):
    """Register all Helm chart-related MCP tools."""

    @mcp.tool(tags={"kubernetes", "helm_charts", "details"})
    async def get_helm_chart(
        chart_name: str, chart_version: str, repo_identifier: Optional[str] = None
    ) -> dict[str, Any] | str:
        """
        Get detailed information about a specific Helm chart. Helm charts are sometimes
        referred to as Kubernetes marketplace.

        This tool retrieves comprehensive details about a specific chart version, including
        metadata, default values, configuration questions, readme documentation, and maintainer info.

        Common Use Cases:
        - View complete chart configuration and default values
        - Understand chart variables and configuration options
        - Read chart documentation and app readme
        - Check maintainer information and chart metadata
        - Retrieve chart source code and home page links

        Args:
            chart_name: Name of the Helm chart (required). Example: 'nginx'
            chart_version: Version of the Helm chart (required). Example: '15.4.0'
            repo_identifier: Repository identifier (optional). Defaults to local repository if not specified

        Returns:
            Dictionary containing:
            - chart: Chart metadata (name, version, app_version, description, home, sources, keywords, maintainers)
            - values: Default configuration values for the chart
            - questions: Configuration questions/variables with types and constraints
            - readme: Chart documentation in Markdown
            - app_readme: Application documentation
            - repo_identifier: Repository identifier used
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameters
        if not chart_name or not chart_name.strip():
            return "Error: chart_name is required and cannot be empty"
        if not chart_version or not chart_version.strip():
            return "Error: chart_version is required and cannot be empty"

        # Encode path parameters for URL safety
        encoded_name = urllib.parse.quote(chart_name, safe="")
        encoded_version = urllib.parse.quote(chart_version, safe="")

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/helm/charts/name/{encoded_name}/version/{encoded_version}"

        # Add optional query parameter
        if repo_identifier:
            url += f"?repoIdentifier={urllib.parse.quote(repo_identifier, safe='')}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving Helm chart '{chart_name}' version '{chart_version}'")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {
                    "chart_name": chart_name,
                    "chart_version": chart_version,
                    "query_time": datetime.now().isoformat(),
                }

                if repo_identifier:
                    result["_request_info"]["repo_identifier"] = repo_identifier
                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving chart: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Helm chart '{chart_name}' version '{chart_version}' not found. Check the chart name and version."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions to access this chart."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return (
                        f"Invalid chart name or version format. Check the parameters."
                    )
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve chart details. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving chart: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "helm_charts", "list", "in_project_repo"})
    async def list_helm_charts() -> dict[str, Any] | str:
        """
        List all available Helm charts in the project repository. Helm charts are
        sometimes referred to as Kubernetes marketplace.

        This tool retrieves a comprehensive list of all Helm charts available in your repository,
        including all versions, metadata, descriptions, and URLs for each chart.

        Common Use Cases:
        - Discover available Helm charts for deployment
        - View all versions of a specific chart
        - Get chart metadata (app version, created date, digest)
        - Find charts by name or keyword

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

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/helm/charts"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info("Listing available Helm charts")

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
                logger.error(f"Network error retrieving charts: {e}")
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
                    return (
                        "Server error. Failed to retrieve chart list. Please try again."
                    )
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving charts: {e}")
                return f"Unexpected error: {str(e)}"
