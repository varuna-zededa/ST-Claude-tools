"""
Zededa MCP tools for image management.

These tools provide agents with a comprehensive interface for querying and managing
application images (app bundles) and EVE OS images in Zedcloud.

Design Principles:
- Tools consolidate related API calls under a single interface to reduce context overhead
- Responses are optimized for agent readability, prioritizing human-interpretable identifiers
- Tools provide sensible defaults and helpful guidance for token-efficient agent behaviors
- Parameter names are unambiguous and self-documenting
"""

from typing import Any, Optional, Literal
import httpx
import urllib.parse
from utility.field_extractors import ImageFieldExtractor, detect_list_response_mode, get_swagger_schema_for_discovery
from utils import (
    is_valid_uuid,
    ZEDEDA_API_BASE,
    USER_AGENT,
    logger,
    load_mock_json,
)
from mock_utils import filter_mock_list, select_mock_fields, filter_mock_by_identifier
from auth import ensure_bearer_token

try:
    from app.prompts.plot_generation_prompt import create_plot_response_structure
except ImportError:
    logger.info(
        "Failed to import create_plot_response_structure from app.prompts.plot_generation_prompt"
    )
    # Fallback if running from different directory context
    try:
        from prompts.plot_generation_prompt import create_plot_response_structure
    except ImportError:
        logger.info(
            "Failed to import create_plot_response_structure from prompts.plot_generation_prompt"
        )
        create_plot_response_structure = None
except Exception as e:
    logger.error("Unexpected error importing create_plot_response_structure", exc_info=True)
    create_plot_response_structure = None


def register_image_tools(mcp):
    """Register all image-related MCP tools."""
    USE_MOCK_API_MCP_DATA = getattr(mcp, "USE_MOCK_API_MCP_DATA", False)
    logger.info(
        f"[TOOL] Image tools registered with USE_MOCK_API_MCP_DATA={USE_MOCK_API_MCP_DATA}"
    )

    @mcp.tool(tags={"images", "lookup by id or name"})
    async def get_image(
        identifier: str, lookup_by: Literal["id", "name"] = "name"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific application image.

        Use this tool when you need to get complete configuration and metadata for an image.
        The tool automatically resolves the image from either its unique ID or human-readable name.

        Args:
            identifier: The image ID or name to look up
            lookup_by: Search method - "id" for image ID lookup or "name" for name lookup (default: "name")

        Returns:
            Dictionary containing image details including ID, name, datastore configuration,
            architecture, image format, and project associations. Returns error message if image not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("images-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for image {lookup_by}='{identifier}'"
                )
                # Use intelligent filtering - auto-detects ID vs name, with fallback
                filtered_mock = filter_mock_by_identifier(
                    mock,
                    identifier,
                    lookup_by=lookup_by,
                    id_field="id",
                    name_field="name"
                )
                if filtered_mock is None:
                    return f"Image not found. Check that the {lookup_by} '{identifier}' is correct."
                return filtered_mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID if looking up by id - if invalid, try as name instead
        if lookup_by == "id" and not is_valid_uuid(identifier):
            logger.info(
                f"Invalid UUID format for identifier '{identifier}', attempting name-based lookup"
            )
            # Try name-based lookup as fallback
            url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/name/{urllib.parse.quote(identifier, safe='')}"
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Authorization": token,
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, headers=headers, timeout=30.0)
                    response.raise_for_status()
                    result = response.json()
                    # Success with name lookup - inform the LLM
                    result["_lookup_note"] = (
                        f"Note: '{identifier}' was provided as an ID but is not a valid UUID. The identifier appears to be a name, and the image was found using a name-based lookup. If this is a name, use lookup_by='name' in future requests."
                    )
                    return result
                except Exception as e:
                    logger.exception(f"Exception during name-based image lookup for identifier '{identifier}'")
                    return f"Invalid image ID format (not a UUID): '{identifier}'. Also attempted name-based lookup but image not found. Please verify the identifier."

        # Build URL based on lookup method
        lookup_endpoint = "id" if lookup_by == "id" else "name"
        encoded_identifier = urllib.parse.quote(identifier, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/{lookup_endpoint}/{encoded_identifier}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving image {lookup_by}='{identifier}'")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"Image not found. Check that the {lookup_by} '{identifier}' is correct."
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "summary", "plot", "visualization"})
    async def get_images_summary(
        page_size: Optional[int] = 20,
        image_type: Optional[str] = "IMAGE_TYPE_APPLICATION",
        page_num: Optional[int] = 1,
        create_plot: bool = False,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Get the summary of images from Zedcloud with optional plot-ready data transformation.

        This tool retrieves a paginated list of images filtered by type, providing
        essential metadata about application bundles or EVE OS images. Can optionally
        transform the data for visualization.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            page_size: Number of items per page (default: 20, max: 50)
            image_type: Type of images to retrieve. Valid values:
                       IMAGE_TYPE_APPLICATION (for app bundles),
                       IMAGE_TYPE_EVE (for EVE OS images)
            page_num: Page number for pagination (default: 1)
            create_plot: If True, wrap response with data and plot_instructions for chart creation (default: False)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of images with metadata including names, IDs,
            architecture, and datastore information. Returns error message on failure.
            If create_plot=True: wrapped as {data: {...}, plot_instructions: {...}}
        """
        # Use the pre-configured ImageFieldExtractor
        field_extractor = ImageFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/images"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("images-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for images summary, type: {image_type}"
                )
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate image_type
        valid_image_types = ["IMAGE_TYPE_APPLICATION", "IMAGE_TYPE_EVE"]
        if image_type not in valid_image_types:
            return f"Invalid image_type '{image_type}'. Must be one of: {', '.join(valid_image_types)}"

        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images?imageType={image_type}&next.pageSize={effective_page_size}&next.pageNum={page_num}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Querying images summary from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Transform for plot if requested (before filtering fields)
                if create_plot and create_plot_response_structure:
                    # Extract architecture distribution for visualization
                    arch_distribution = {}
                    total_images = 0

                    if isinstance(result, dict) and "list" in result:
                        for image in result.get("list", []):
                            total_images += 1
                            arch = image.get("imageArch", "Unknown")
                            if arch:
                                arch_distribution[arch] = (
                                    arch_distribution.get(arch, 0) + 1
                                )

                    # Create plot-ready response
                    transformed = {
                        "total_images": total_images,
                        "image_type": image_type,
                        "architecture_distribution": arch_distribution,
                        "raw_data": result,
                    }

                    logger.debug(
                        "is create_plot_response_structure available? %s",
                        create_plot_response_structure is not None,
                    )
                    logger.debug("create_plot parameter is %s", create_plot)
                    logger.debug(
                        f"Transformed {total_images} images into plot data with {len(arch_distribution)} architectures"
                    )

                    metric_context = f"Image distribution for {image_type} showing {total_images} total images across {len(arch_distribution)} architectures. Default chart type is pie or bar chart."
                    return create_plot_response_structure(transformed, metric_context)
                elif create_plot and not create_plot_response_structure:
                    # User requested plot but function unavailable
                    logger.warning(
                        "Plot creation requested (create_plot=True) but create_plot_response_structure "
                        "is unavailable due to import failure. Returning raw data instead."
                    )

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"all_images", "images"})
    async def get_all_images(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Get all application images from Zedcloud.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Note: The `projectAccessList` field is ALWAYS empty in this list response.
        To retrieve project access information for an image, make a separate call to
        `get_image` with the image's id or name — the detail response includes
        the populated `projectAccessList`.

        Args:
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of application images with metadata including names,
            IDs, architecture, datastore information, and project associations.
        """
        # Use the pre-configured ImageFieldExtractor
        field_extractor = ImageFieldExtractor()

        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/images"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)

        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("images-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for application images")
                filtered_mock = filter_mock_list(
                    mock,
                    page_size=effective_page_size,
                    page_num=page_num,
                )
                return field_extractor.filter_response(
                    filtered_mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images?next.pageSize={effective_page_size}&next.pageNum={page_num}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Querying application images from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "eve-images", "eve os", "lookup by id"})
    async def get_eve_image(
        identifier: str, lookup_by: Literal["id"] = "id"
    ) -> dict[str, Any] | str:
        """
        Retrieve detailed information about a specific EVE OS image.

        Use this tool when you need to get complete configuration and metadata for an EVE image.

        Args:
            identifier: The EVE image ID to look up
            lookup_by: Search method - currently only "id" is supported (default: "id")

        Returns:
            Dictionary containing EVE image details including ID, version, architecture,
            compatibility, and image format. Returns error message if image not found.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("images-detail.json")
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for EVE image {lookup_by}='{identifier}'"
                )
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate UUID
        if not is_valid_uuid(identifier):
            return f"Invalid EVE image ID format (not a UUID): '{identifier}'. Please provide a valid EVE image ID."

        encoded_identifier = urllib.parse.quote(identifier, safe="")
        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/eve/id/{encoded_identifier}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving EVE image {lookup_by}='{identifier}'")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"EVE image not found. Check that the ID '{identifier}' is correct."
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "eve-images", "eve os"})
    async def get_eve_images(
        page_size: Optional[int] = 20,
        page_num: Optional[int] = 1,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Get all EVE OS images from Zedcloud.

        This tool retrieves a paginated list of all EVE OS images available
        in the Zedcloud environment.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            page_size: Number of items per page (default: 20, max: 50)
            page_num: Page number for pagination (default: 1)
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of EVE OS images with metadata including versions,
            architecture, and compatibility information.
        """
        # Use the pre-configured ImageFieldExtractor
        field_extractor = ImageFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/images/eve"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json("images-list.json", required=USE_MOCK_API_MCP_DATA)
            if mock is not None:
                logger.info("[MOCK] Returning mock data for EVE images")
                return field_extractor.filter_response(
                    mock,
                    additional_fields,
                    return_complete=return_complete
                )

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/eve?next.pageSize={effective_page_size}&next.pageNum={page_num}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Querying EVE images from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "projects", "access control"})
    async def query_image_project_list(
        ids: Optional[list[str]] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        DO NOT USE for retrieving projectAccessList for images. This bulk endpoint
        is unreliable on current ZedCloud deployments and frequently returns 400.
        To retrieve project access information for an image, call `get_image` with
        the image's id or name — the detail response includes the populated
        `projectAccessList`.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            ids: List of image IDs to query for common project access
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of projects with access to the specified images.
        """
        # Detect mode based on parameters (using ImageFieldExtractor for consistency)
        field_extractor = ImageFieldExtractor()
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/images/projects"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "images-project-list.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for image project list")
                if return_complete:
                    return mock
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

        if ids:
            for id_val in ids:
                params.setdefault("ids", []).append(id_val)
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/projects"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Querying image project list from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Return complete response if no filtering requested
                if return_complete:
                    return result

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "baseos", "eve os", "latest"})
    async def query_latest_baseos_images(
        name_pattern: Optional[str] = None,
        fields: Optional[list[str]] = None,
        page_token: Optional[str] = None,
        page_num: Optional[int] = 1,
        page_size: Optional[int] = 20,
        total_pages: Optional[int] = None,
        discover_schema: Optional[bool] = None,
        return_basic_fields: Optional[bool] = None,
        additional_fields: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any] | str:
        """
        Query latest version of EVE OS image for each hardware architecture.

        This tool retrieves the most recent EVE OS images available for different
        hardware architectures, useful for planning upgrades and understanding
        current image availability.

        Response modes:
        - Default (no flags): Returns ALL fields from ZedCloud (complete response, safest fallback)
        - Discovery mode (discover_schema=true): Returns swagger schema structure (NO API call) showing all available fields with descriptions
        - Filtered mode (return_basic_fields=true): Returns BASIC fields only, plus any additional_fields specified

        Args:
            name_pattern: Filter by image name pattern (DOES NOT support direct wildcards like '*', use substring matching like 'eve-os-*' instead)
            fields: Specific fields to return in the response
            page_token: Page token for pagination
            page_num: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 20, max: 50)
            total_pages: Total number of pages to fetch
            discover_schema: Enable discovery mode (see Response modes above)
            return_basic_fields: Enable filtered mode (see Response modes above)
            additional_fields: Extra fields dict for filtered mode, e.g. {"fieldName": true}

        Returns:
            Dictionary containing list of latest EVE OS images per architecture with
            version information and compatibility details.
        """
        # Use the pre-configured ImageFieldExtractor
        field_extractor = ImageFieldExtractor()
        
        # Detect mode based on parameters
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, return_basic_fields, additional_fields)
        
        # DISCOVERY MODE: Return swagger schema structure immediately (NO API call)
        api_endpoint = "/api/v1/apps/images/baseos/latest"
        if is_discovery_mode:
            swagger_structure = get_swagger_schema_for_discovery(api_endpoint)
            if swagger_structure:
                logger.info("Discovery mode: returning swagger schema structure (no API call)")
                return swagger_structure
        
        effective_page_size = min(page_size or 20, 50)
        
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "images-baseos-latest.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info("[MOCK] Returning mock data for latest BaseOS images")
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

        if name_pattern:
            params["namePattern"] = name_pattern
        if fields:
            for field in fields:
                params.setdefault("fields", []).append(field)
        if page_token:
            params["next.pageToken"] = page_token
        if page_num is not None:
            params["next.pageNum"] = str(page_num)
        params["next.pageSize"] = str(effective_page_size)
        if total_pages is not None:
            params["next.totalPages"] = str(total_pages)

        url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/baseos/latest"

        # Handle array parameters properly for URL encoding
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
            else:
                query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

        if query_parts:
            url += "?" + "&".join(query_parts)

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }
        logger.info(f"Querying latest BaseOS images from URL: {url}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                # Filter the response using the field extractor
                return field_extractor.filter_response(
                    result,
                    additional_fields,
                    return_complete=return_complete
                )

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"

    @mcp.tool(tags={"images", "baseos", "eve os", "latest", "architecture"})
    async def get_latest_baseos_image_by_arch(image_arch: str) -> dict[str, Any] | str:
        """
        Get latest version of EVE OS image for a specific hardware architecture.

        This tool retrieves the most recent EVE OS image for a particular hardware
        class, useful for device provisioning and upgrade planning.

        Args:
            image_arch: Hardware architecture/class to query for (e.g., "amd64", "arm64")
        Returns:
            Dictionary containing the latest EVE OS image details for the specified
            architecture including version, ID, and compatibility information.
        """
        if USE_MOCK_API_MCP_DATA:
            mock = load_mock_json(
                "images-baseos-latest-arch.json", required=USE_MOCK_API_MCP_DATA
            )
            if mock is not None:
                logger.info(
                    f"[MOCK] Returning mock data for latest BaseOS image, arch: {image_arch}"
                )
                return mock

        token = await ensure_bearer_token()
        if isinstance(token, str) and "Authorization header" in token:
            return token

        # Validate required parameter
        if not image_arch or not image_arch.strip():
            return "Error: image_arch is required and cannot be empty"

        encoded_arch = urllib.parse.quote(image_arch, safe="")
        url = (
            f"{ZEDEDA_API_BASE}/api/v1/apps/images/baseos/latest/hwclass/{encoded_arch}"
        )

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Authorization": token,
        }

        logger.info(f"Retrieving latest BaseOS image for architecture: {image_arch}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error - GET {url}: {e}")
                return f"Request failed: {e}"
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP status error - GET {url}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 404:
                    return f"No latest BaseOS image found for architecture: {image_arch}. Check that the architecture name is correct."
                return f"HTTP error {e.response.status_code}: {e.response.text}"
            except Exception as e:
                logger.error(f"Unexpected error - GET {url}: {e}")
                return f"Unexpected error: {e}"
