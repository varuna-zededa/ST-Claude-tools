"""
Zededa MCP tools for hardware model management.

These tools provide agents with a comprehensive interface for querying and
managing hardware model (sysmodel) information from Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import urllib.parse
from utility.field_extractors import ModelFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import make_zededa_request, ZEDEDA_API_BASE, logger, load_mock_json
from mock_utils import filter_mock_list, filter_mock_by_identifier
from auth import ensure_bearer_token


def register_hardware_model_tools(mcp):
    """Register all hardware model-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Hardware model tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"all_models", "hardware_models", "sysmodels"})
    async def get_all_models(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            brand_id: Optional[list[str]] = None,
            origin_type: Optional[str] = None,
            include_global: Optional[bool] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = None,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query hardware model records with optimized response filtering.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Only summary of the records required (boolean)
            name_pattern: Model name pattern to be matched (supports wildcards)
            brand_id: List of system defined universally unique IDs of the brand
            origin_type: Origin of object. Valid values:
                        ORIGIN_UNSPECIFIED, ORIGIN_IMPORTED, ORIGIN_LOCAL, 
                        ORIGIN_GLOBAL, ORIGIN_APP_PROFILE_LOCAL
            include_global: Include global models that are not imported (boolean)
            page_token: Page token for pagination
            page_num: Page number for pagination
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of models with requested fields.
        """
        # Use the pre-configured ModelFieldExtractor
        field_extractor = ModelFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/sysmodels"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sysmodels-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for hardware models list")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    name_pattern=name_pattern,
                    brand_id=brand_id,
                    origin_type=origin_type,
                    include_global=include_global,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked get_all_models tool")

        # Valid origin types
        valid_origin_types = [
            "ORIGIN_UNSPECIFIED", "ORIGIN_IMPORTED", "ORIGIN_LOCAL",
            "ORIGIN_GLOBAL", "ORIGIN_APP_PROFILE_LOCAL"
        ]

        # Validate origin_type if provided
        if origin_type and origin_type not in valid_origin_types:
            return f"Invalid origin_type '{origin_type}'. Must be one of: {', '.join(valid_origin_types)}"

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if brand_id:
            for bid in brand_id:
                params.setdefault("brandId", []).append(bid)
        if origin_type:
            params["originType"] = origin_type
        if include_global is not None:
            params["includeGlobal"] = str(include_global).lower()
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(
                        f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve hardware models."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"get_all_global_models", "hardware", "models", "global"})
    async def get_all_global_models(
            summary: Optional[bool] = None,
            name_pattern: Optional[str] = None,
            brand_id: Optional[list[str]] = None,
            origin_type: Optional[str] = None,
            include_global: Optional[bool] = None,
            page_token: Optional[str] = None,
            page_num: Optional[int] = None,
            page_size: Optional[int] = 20,
            total_pages: Optional[int] = None,
            discover_schema: Optional[bool] = None,
            return_basic_fields: Optional[bool] = None,
            additional_fields: Optional[dict[str, bool]] = None) -> dict[str, Any] | str:
        """
        Query global hardware model records with optimized response filtering.
        
        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified
        
        Args:
            summary: Only summary of the records required (boolean)
            name_pattern: Model name pattern to be matched (supports wildcards)
            brand_id: List of system defined universally unique IDs of the brand
            origin_type: Origin of object. Valid values:
                        ORIGIN_UNSPECIFIED, ORIGIN_IMPORTED, ORIGIN_LOCAL, 
                        ORIGIN_GLOBAL, ORIGIN_APP_PROFILE_LOCAL
            include_global: Include global models that are not imported (boolean)
            page_token: Page token for pagination
            page_num: Page number for pagination
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of global models with requested fields.
        """
        # Use the pre-configured ModelFieldExtractor
        field_extractor = ModelFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/sysmodels/global"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sysmodels-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for global hardware models list")
                # Apply filters to mock data - pass ALL parameters
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                    summary=summary,
                    name_pattern=name_pattern,
                    brand_id=brand_id,
                    origin_type=origin_type,
                    include_global=include_global,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        logger.debug("Invoked query_zededa_global_hardware_models tool")

        # Valid origin types
        valid_origin_types = [
            "ORIGIN_UNSPECIFIED", "ORIGIN_IMPORTED", "ORIGIN_LOCAL",
            "ORIGIN_GLOBAL", "ORIGIN_APP_PROFILE_LOCAL"
        ]

        # Validate origin_type if provided
        if origin_type and origin_type not in valid_origin_types:
            return f"Invalid origin_type '{origin_type}'. Must be one of: {', '.join(valid_origin_types)}"

        # Build query parameters
        params = {}

        if summary is not None:
            params["summary"] = str(summary).lower()
        if name_pattern:
            params["namePattern"] = name_pattern
        if brand_id:
            for bid in brand_id:
                params.setdefault("brandId", []).append(bid)
        if origin_type:
            params["originType"] = origin_type
        if include_global is not None:
            params["includeGlobal"] = str(include_global).lower()
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        if effective_page_size is not None:
            params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        # Build URL with query parameters
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels/global"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(
                        f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return "Failed to retrieve global hardware models."

        # Filter the response using the field extractor
        return field_extractor.filter_response(
            response,
            additional_fields,
            return_complete=return_complete
        )

    @mcp.tool(tags={"hardware_model", "model", "sysmodel", "lookup_by_id_or_name"})
    async def get_model(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific hardware model.

        Use this tool when you need to get complete information for a hardware model (sysmodel).
        The tool automatically resolves the model from either its unique ID or human-readable name.

        Args:
            identifier: The model ID or name to look up
            lookup_by: Search method - "id" for model ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing model details including ID, name, brand, and configuration.
            Returns error message if model not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"sysmodels-detail.json")
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for hardware model {lookup_by}={identifier}")
                # Use intelligent filtering - auto-detects ID vs name, with fallback
                filtered_mock = filter_mock_by_identifier(
                    mock,
                    identifier,
                    lookup_by=lookup_by,
                    id_field="id",
                    name_field="name"
                )
                if filtered_mock is None:
                    return f"Hardware model not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return f"Error: identifier parameter is required and cannot be empty"

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels/{lookup_endpoint}/{encoded_identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Hardware model not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"global_hardware_model", "model", "sysmodel", "lookup_by_id_or_name"})
    async def get_global_model(
        identifier: str,
        lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific global hardware model.

        Use this tool when you need to get complete information for a global hardware model (sysmodel).
        The tool automatically resolves the model from either its unique ID or human-readable name.

        Args:
            identifier: The model ID or name to look up
            lookup_by: Search method - "id" for model ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing global model details including ID, name, brand, and configuration.
            Returns error message if model not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"sysmodels-detail.json")
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for global hardware model {lookup_by}={identifier}")
                # Use intelligent filtering - auto-detects ID vs name, with fallback
                filtered_mock = filter_mock_by_identifier(
                    mock,
                    identifier,
                    lookup_by=lookup_by,
                    id_field="id",
                    name_field="name"
                )
                if filtered_mock is None:
                    return f"Global hardware model not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not identifier or not identifier.strip():
            return f"Error: identifier parameter is required and cannot be empty"

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels/global/{lookup_endpoint}/{encoded_identifier}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Global hardware model not found. Check that the {lookup_by} '{identifier}' is correct."
        return response

    @mcp.tool(tags={"pcr_templates_by_model_id", "hardware", "models", "pcr", "templates"})
    async def get_all_pcr_templates_for_model_id(
            id: str,
            name: Optional[str] = None,
            eve_image_version: Optional[str] = None,
            name_pattern: Optional[str] = None,
            eve_image_version_pattern: Optional[str] = None) -> dict[str, Any] | str:
        """
        Query PCR template records for a hardware model.
        
        Args:
            id: System defined universally unique ID of the model (required)
            name: PCR template name
            eve_image_version: PCR template eve version
            name_pattern: PCR template name pattern to be matched
            eve_image_version_pattern: PCR template eve image version pattern to be matched
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("sysmodels-list.json",
                                  required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for PCR templates for model id={id}")
                # Use intelligent filtering by ID, then apply list filters
                filtered_mock = filter_mock_by_identifier(
                    mock, id, lookup_by="id", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"Hardware model with ID '{id}' not found."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not id or not id.strip():
            return "Error: id parameter is required and cannot be empty"

        # Build URL
        encoded_id = urllib.parse.quote(id, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels/id/{encoded_id}/pcrtemplates"

        # Build query parameters
        query_params = []
        if name:
            query_params.append(f"name={urllib.parse.quote(name)}")
        if eve_image_version:
            query_params.append(
                f"eveImageVersion={urllib.parse.quote(eve_image_version)}")
        if name_pattern:
            query_params.append(
                f"namePattern={urllib.parse.quote(name_pattern)}")
        if eve_image_version_pattern:
            query_params.append(
                f"eveImageVersionPattern={urllib.parse.quote(eve_image_version_pattern)}"
            )

        if query_params:
            url += "?" + "&".join(query_params)

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve PCR templates for model ID: {id}"

        return response

    @mcp.tool(tags={"pcr_template_by_name", "hardware", "models", "pcr", "templates"})
    async def get_pcr_template_by_name(
            model_id: str,
            name: str) -> dict[str, Any] | str:
        """
        Query a specific PCR template by name for a hardware model.
        
        Args:
            model_id: Device model identifier (required)
            name: User defined name of the PCR template, unique across a model (required)
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(f"sysmodels-detail.json")
            if mock is not None:
                logger.info(f"[MOCK] Returning mock data for PCR template name={name} for model={model_id}")
                # Use intelligent filtering by name
                filtered_mock = filter_mock_by_identifier(
                    mock, name, lookup_by="name", id_field="id", name_field="name"
                )
                if filtered_mock is None:
                    return f"PCR template with name '{name}' not found for model '{model_id}'."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        if not model_id or not model_id.strip():
            return "Error: model_id parameter is required and cannot be empty"

        if not name or not name.strip():
            return "Error: name parameter is required and cannot be empty"

        # Build URL
        encoded_model_id = urllib.parse.quote(model_id, safe='')
        encoded_name = urllib.parse.quote(name, safe='')
        url = f"{ZEDEDA_API_BASE}/api/v1/sysmodels/id/{encoded_model_id}/pcrtemplates/name/{encoded_name}"

        response = await make_zededa_request(url, "get", token)
        if response is None:
            return f"Failed to retrieve PCR template '{name}' for model ID: {model_id}"

        return response
