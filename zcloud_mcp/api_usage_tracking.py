"""
Zededa MCP tools for Orchestrator Service - API Usage Tracking.
"""
from typing import Any, Optional
import urllib.parse
from utility.field_extractors import ApiUsageFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE
from auth import ensure_bearer_token


def register_api_usage_tracking_tools(mcp):
    """Register all API usage tracking-related MCP tools (GET methods only)."""

    @mcp.tool(tags={"zedcloud", "orchestrator", "api_usage"})
    async def query_zededa_orchestrator_api_usage(
            enterprise_ids: Optional[list[str]] = None,
            user_agents: Optional[list[str]] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query API usage statistics from Zededa Orchestrator Service.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            enterprise_ids: Filter by enterprise IDs
            user_agents: Filter by user agents
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}
            
        Returns:
            Dictionary containing API usage statistics with requested fields
        """
        # Use the pre-configured ApiUsageFieldExtractor
        field_extractor = ApiUsageFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apiusage"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Build query parameters
        params = {}

        if enterprise_ids:
            for enterprise_id in enterprise_ids:
                params.setdefault("enterpriseIDs", []).append(enterprise_id)
        if user_agents:
            for user_agent in user_agents:
                params.setdefault("userAgents", []).append(user_agent)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/apiusage"
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
            return "Failed to retrieve API usage statistics."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )
