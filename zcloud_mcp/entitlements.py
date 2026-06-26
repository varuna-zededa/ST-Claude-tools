"""
Entitlements and Reports Management.

This module provides MCP tools for managing entitlements and generating
reports in ZedCloud. Entitlements define resource quotas and capabilities
for enterprises, while reports provide analytics on usage and resources.

Design Principles:
- All list operations support pagination via next_page_token
- Consistent error messages following the pattern:
    "Failed to retrieve {resource}."
- Mock data support via USE_MOCK_API_MCP_DATA for testing
- Separate tools for different report types (apps, devices, plugins, etc.)
"""

import logging
from typing import Any, Optional
import urllib.parse
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json
from auth import ensure_bearer_token

logger = logging.getLogger(__name__)


def register_entitlements_tools(mcp):
    """Register all entitlement-related MCP tools (GET methods only)."""
    logger.info("Registering entitlements tools with MCP server")
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"entitlements", "resource_quotas"})
    async def get_entitlements(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get entitlement data for an enterprise.

        Retrieves the entitlements (resource quotas and capabilities)
        configured for an enterprise.

        Args:
            enterprise_id: ID of the enterprise to get entitlements for.

        Returns:
            dict: Entitlement data for the enterprise.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements not found.")
                return "Mock data for entitlements not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/entitlements"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve entitlements."
        return response

    @mcp.tool(tags={"entitlements", "allowed_enterprise"})
    async def get_allowed_enterprises_for_entitlements(
            summary: Optional[bool] = None,
            sfdc_id: Optional[str] = None,
            hubspot_id: Optional[str] = None,
            project: Optional[str] = None,
            name_pattern: Optional[str] = None,
            all: Optional[bool] = None,
            role_name: Optional[str] = None,
            size: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """
        Get enterprises for which the user can view/edit entitlements.

        Retrieves the list of enterprises for which the logged-in user
        has permissions to view or edit entitlements.

        Args:
            summary: Return summary information only.
            sfdc_id: Filter by Salesforce ID.
            hubspot_id: Filter by HubSpot ID.
            project: Filter by project name.
            name_pattern: Filter by enterprise name pattern.
            all: Include all enterprises.
            role_name: Filter by role name.
            size: Filter by size.
            page_token: Token for pagination.
            page_num: Page number for pagination (default: 1).
            page_size: Number of results per page (default: 20, max: 50).
            total_pages: Total number of pages to retrieve.

        Returns:
            dict: List of enterprises with entitlement access.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if sfdc_id:
            params["SfdcId"] = sfdc_id
        if hubspot_id:
            params["HubspotId"] = hubspot_id
        if project:
            params["project"] = project
        if name_pattern:
            params["namePattern"] = name_pattern
        if all is not None:
            params["all"] = str(all).lower()
        if role_name:
            params["roleName"] = role_name
        if size:
            params["size"] = size
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/entitlements/allowedenterprises"
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
            return "Failed to retrieve allowed enterprises for entitlements."
        return response

    @mcp.tool(tags={"reports", "allowed_enterprise"})
    async def get_allowed_enterprises_for_reports(
            summary: Optional[bool] = None,
            sfdc_id: Optional[str] = None,
            hubspot_id: Optional[str] = None,
            project: Optional[str] = None,
            name_pattern: Optional[str] = None,
            all: Optional[bool] = None,
            role_name: Optional[str] = None,
            size: Optional[str] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None) -> dict[str, Any] | str:
        """
        Get enterprises for which the user can query reports.

        Retrieves the list of enterprises for which the logged-in user
        has permissions to query reports and analytics.

        Args:
            summary: Return summary information only.
            sfdc_id: Filter by Salesforce ID.
            hubspot_id: Filter by HubSpot ID.
            project: Filter by project name.
            name_pattern: Filter by enterprise name pattern.
            all: Include all enterprises.
            role_name: Filter by role name.
            size: Filter by size.
            page_token: Token for pagination.
            page_num: Page number for pagination (default: 1).
            page_size: Number of results per page (default: 20, max: 50).
            total_pages: Total number of pages to retrieve.

        Returns:
            dict: List of enterprises with report access.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if sfdc_id:
            params["SfdcId"] = sfdc_id
        if hubspot_id:
            params["HubspotId"] = hubspot_id
        if project:
            params["project"] = project
        if name_pattern:
            params["namePattern"] = name_pattern
        if all is not None:
            params["all"] = str(all).lower()
        if role_name:
            params["roleName"] = role_name
        if size:
            params["size"] = size
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if page_size is not None:
            params["next.pageSize"] = str(min(page_size, 50))
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/allowedenterprises"
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
            return "Failed to retrieve allowed enterprises for reports."
        return response

    @mcp.tool(tags={"reports", "app_instances", "analytics"})
    async def get_app_instance_report(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get application instance report for an enterprise.

        Retrieves a report of application instances deployed
        within an enterprise.

        Args:
            enterprise_id: Optional enterprise ID to filter by specific enterprise.

        Returns:
            dict: Application instance report data.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/apps/instance"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve application instance report."
        return response

    @mcp.tool(tags={"reports", "devices", "analytics"})
    async def get_device_report(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get device report for an enterprise.

        Retrieves a report of devices (edge nodes) registered
        within an enterprise.

        Args:
            enterprise_id: Optional enterprise ID to filter by specific enterprise.

        Returns:
            dict: Device report data.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/device"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve device report."
        return response

    @mcp.tool(tags={"reports", "plugins", "analytics"})
    async def get_plugin_report(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get plugin report for an enterprise.

        Retrieves a report of plugins (third party integrations)
        within an enterprise.

        Args:
            enterprise_id: Optional enterprise ID to filter by specific enterprise.

        Returns:
            dict: Plugin report data.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/plugin"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve plugin report."
        return response

    @mcp.tool(tags={"reports", "projects", "analytics"})
    async def get_project_report(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get project report for an enterprise.

        Retrieves a report of projects configured within an enterprise.

        Args:
            enterprise_id: Optional enterprise ID to filter by specific enterprise.

        Returns:
            dict: Project report data.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/project"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve project report."
        return response

    @mcp.tool(tags={"reports", "users", "analytics"})
    async def get_user_report(
            enterprise_id: Optional[str] = None) -> dict[str, Any] | str:
        """
        Get user report for an enterprise.

        Retrieves a report of users registered within an enterprise.

        Args:
            enterprise_id: Optional enterprise ID to filter by specific enterprise.

        Returns:
            dict: User report data.
            str: Error message if the request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("entitlements-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock
            else:
                logger.warning(
                    "Mock data for entitlements list not found.")
                return "Mock data for entitlements list not found."

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        params = {}
        if enterprise_id:
            params["tenantId"] = enterprise_id

        url = f"{ZEDEDA_API_BASE}/api/v1/reports/user"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve user report."
        return response
