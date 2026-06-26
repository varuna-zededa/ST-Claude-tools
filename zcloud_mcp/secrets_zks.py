"""
Zededa MCP tools for Kubernetes secrets management.

These tools provide agents with a comprehensive interface for querying and managing
Kubernetes secrets used for authentication and configuration within Zededa's infrastructure.

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


def register_secret_tools(mcp):
    """Register all Kubernetes secrets-related MCP tools."""

    @mcp.tool(tags={"kubernetes", "secrets", "details"})
    async def get_kubernetes_secret(secret_id: str) -> dict[str, Any] | str:
        """
        Get detailed information about a specific Kubernetes secret.

        This tool retrieves comprehensive details about a secret, including its metadata,
        type, status, and decrypted data (SSH keys, credentials, tokens, etc.).

        Common Use Cases:
        - View complete secret configuration and data
        - Retrieve SSH keys or API tokens for use in deployments
        - Check basic auth credentials (username/password)
        - Verify secret status and health
        - Review secret metadata and ownership information

        Args:
            secret_id: Unique identifier of the secret (required). Example: 'secret-abc123'

        Returns:
            Dictionary containing:
            - id: Secret unique identifier
            - metadata: Name, type (SSH, BASIC_AUTH, etc.), project_id, creation_timestamp, state
            - data: Decrypted secret data (ssh_private_key, username/password, token, etc.)
            - _type: Secret type identifier
            - kind: Secret kind
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not secret_id or not secret_id.strip():
            return "Error: secret_id is required and cannot be empty"

        # Encode secret ID for URL safety
        encoded_id = urllib.parse.quote(secret_id, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/secrets/id/{encoded_id}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving Kubernetes secret for ID '{secret_id}'")

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Redact sensitive credential values — return key names so the
                # caller knows what fields exist, but never expose raw secrets.
                if "data" in result and isinstance(result["data"], dict):
                    result["data"] = {k: "[REDACTED]" for k in result["data"]}

                result["_request_info"] = {
                    "secret_id": secret_id,
                    "query_time": datetime.now().isoformat(),
                }

                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving secret: {e}")
                return f"Network error. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 404:
                    return f"Kubernetes secret with ID '{secret_id}' not found. Check the secret ID."
                elif e.response.status_code == 403:
                    return (
                        "Access denied. Check your permissions to access this secret."
                    )
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 400:
                    return f"Invalid secret ID format. Check the secret ID."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve secret. Please try again."
                return f"HTTP error {e.response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error retrieving secret: {e}")
                return f"Unexpected error: {str(e)}"

    @mcp.tool(tags={"kubernetes", "secrets", "list"})
    async def list_all_kubernetes_secrets(
        project_id: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """
        List all Kubernetes secrets with metadata and status information.

        This tool retrieves a list of all configured Kubernetes secrets, including their
        metadata, type, and status. Secret data is not included in list responses for security.

        Common Use Cases:
        - View all configured secrets and their types
        - Monitor secret status and health
        - Filter secrets by project
        - Find secrets by name or type (SSH, Basic Auth, etc.)
        - Audit secret configuration across infrastructure

        Args:
            project_id: Optional filter to list secrets for a specific project

        Returns:
            Dictionary containing:
            - secrets: List of secret configurations with metadata and status
            - total_count: Total number of secrets
            - _request_info: Request metadata
        """
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/cluster/instances/kubernetes/secrets"

        # Add optional query parameter
        if project_id:
            url += f"?projectId={urllib.parse.quote(project_id, safe='')}"

        # Prepare headers
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(
            f"Listing Kubernetes secrets{' for project ' + project_id if project_id else ''}"
        )

        # Make the request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Add metadata about the request
                result["_request_info"] = {"query_time": datetime.now().isoformat()}

                if project_id:
                    result["_request_info"]["project_id"] = project_id
                return result

            except httpx.RequestError as e:
                logger.error(f"Network error retrieving secrets: {e}")
                return f"Network error. Please check your connection and try again. Error: {str(e)}"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}")
                if e.response.status_code == 400:
                    return "Invalid request parameters. Check project_id format if provided."
                elif e.response.status_code == 403:
                    return "Access denied. Check your permissions."
                elif e.response.status_code == 401:
                    return "Authentication failed. Check your credentials."
                elif e.response.status_code == 500:
                    return "Server error. Failed to retrieve secrets. Please try again."
                return f"HTTP error {e.response.status_code}. Please try again."
            except Exception as e:
                logger.error(f"Unexpected error retrieving secrets: {e}")
                return f"Unexpected error: {str(e)}"
