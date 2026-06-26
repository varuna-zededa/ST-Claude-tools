"""
Zededa MCP tools for artifact management.
"""
from typing import Any, Optional
import urllib.parse
from utility.field_extractors import ArtifactFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, load_mock_json, logger
from auth import ensure_bearer_token


def register_artifact_tools(mcp):
    """Register all artifact-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)

    @mcp.tool(tags={"artifacts"})
    async def query_artifacts(
            summary: Optional[bool] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = 1,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query artifact files with comprehensive filtering options.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Return summary information only
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing list of artifacts with requested fields
        """
        # Use the pre-configured ArtifactFieldExtractor
        field_extractor = ArtifactFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/artifacts"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("artifacts-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/artifacts"
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
            return "Failed to retrieve artifacts."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"artifact_file_download"})
    async def get_artifact_stream(
            id: str) -> dict[str, Any] | str:
        """Download artifact file chunk by chunk from the file storage."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("artifacts-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/artifacts/id/{id}"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve artifact stream for ID: {id}."
        return response

    @mcp.tool(tags={"artifact_signed_url"})
    async def get_artifact_signed_url(
            id: str) -> dict[str, Any] | str:
        """Generate a signed URL for accessing the artifact resource from datastore (S3, Azure, etc.)."""
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("artifacts-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/artifacts/id/{id}/url"
        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to get signed URL for artifact ID: {id}."
        return response
