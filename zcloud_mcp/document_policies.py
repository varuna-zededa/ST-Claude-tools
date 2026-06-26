"""
Zededa MCP tools for terms and conditions (document policies) management.

These tools provide agents with a comprehensive interface for querying and
managing terms and conditions documents from Zedcloud. Document policies
represent legal agreements, terms of service, and compliance documents
that users must accept.

Note: Document policies are NOT related to project policies or app profile policies.
These are specifically for legal/compliance terms and conditions.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import urllib.parse
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, logger
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_document_policies_tools(mcp):
    """Register all terms and conditions (document policy) related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Terms and conditions tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"terms_and_conditions", "document_policies", "legal", "compliance"})
    async def get_document_policies(
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
        total_pages: Optional[int] = None,
    ) -> dict[str, Any] | str:
        """
        Query terms and conditions documents from Zededa with comprehensive filtering options.

        This tool provides filtering and pagination options to query terms and conditions
        (document policies) from the ZedCloud platform. These represent legal agreements,
        terms of service, and compliance documents that users must accept.

        Note: This is NOT for project policies or app profile policies. Use this tool
        specifically for legal/compliance terms and conditions documents.

        Args:
            summary: Return summary information only (boolean)
            sfdc_id: Filter by Salesforce ID
            hubspot_id: Filter by HubSpot ID
            project: Filter by project name
            name_pattern: Filter by document name pattern (supports wildcards)
            all: Include all documents regardless of scope
            role_name: Filter by associated role name
            size: Filter by size
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch

        Returns:
            Dictionary containing list of terms and conditions documents with pagination info.
            Returns error message if request fails.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "document-policies-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                # Apply filters to mock data - pass ALL parameters
                effective_page_size = min(page_size or 20, 50)
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    sfdc_id=sfdc_id,
                    hubspot_id=hubspot_id,
                    project=project,
                    name_pattern=name_pattern,
                    all=all,
                    role_name=role_name,
                    size=size,
                )
                return filtered_mock

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

        url = f"{ZEDEDA_API_BASE}/api/v1/cloud/policies"
        if params:
            query_parts = []
            for key, value in params.items():
                if isinstance(value, list):
                    for item in value:
                        query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
                else:
                    query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve terms and conditions documents."

        return response

    @mcp.tool(
        tags={
            "terms_and_conditions",
            "document_policy",
            "legal",
            "lookup_by_id_or_name",
        }
    )
    async def get_document_policy(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific terms and conditions document.

        Use this tool when you need to get complete details for a terms and conditions document.
        The tool automatically resolves the document from either its unique ID or human-readable name.

        Note: This is NOT for project policies or app profile policies. Use this tool
        specifically for legal/compliance terms and conditions documents.

        Args:
            identifier: The document ID or name to look up
            lookup_by: Search method - "id" for document ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing document details including ID, name, content, version, and acceptance status.
            Returns error message if document not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("document-policies-detail.json")
            if mock is not None:
                # Use intelligent filtering - auto-detects ID vs name
                filtered_mock = filter_mock_by_identifier(
                    mock, identifier, lookup_by=lookup_by, id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Terms and conditions document not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        url = f"{ZEDEDA_API_BASE}/api/v1/cloud/policies/{lookup_endpoint}/{identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Terms and conditions document not found. Check that the {lookup_by} '{identifier}' is correct."
        return response
