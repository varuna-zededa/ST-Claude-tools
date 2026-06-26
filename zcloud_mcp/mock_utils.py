"""
Mock data utilities for MCP tools.

This module provides utilities to make mock data responses parameter-aware,
allowing filters and queries to work realistically in mock mode for testing.
"""

from typing import Any, Optional, Union
import re
from datetime import datetime
from logging_config import setup_logging
from pathlib import Path
import os

# Setup logging
log_file_path = Path(os.path.dirname(os.path.abspath(__file__))) / "zededa_mcp.log"
logger = setup_logging(__name__, str(log_file_path))


def _find_list_in_data(data: dict[str, Any]) -> tuple[Optional[str], list]:
    """
    Find the list of items in Zededa API mock data response.
    
    Zededa API Standard Structure:
        All list endpoints follow this pattern:
        {
            "summaryByXXX": {...},  // Optional summaries
            "list": [...],          // Always "list" key
            "next": {...},          // Always "next" pagination
            "totalCount": 123       // Sometimes present
        }
    
    Strategy:
    1. Check for standard "list" key first (Zededa convention)
    2. Fallback to other common keys for flexibility
    3. Return None if no suitable list found
    
    Args:
        data: Mock data dictionary
    
    Returns:
        Tuple of (list_key, items_list) or (None, [])
    """
    # Standard Zededa API uses "list" key for all list responses
    if "list" in data and isinstance(data["list"], list):
        items = data["list"]
        logger.debug(f"[MOCK] Found standard 'list' key with {len(items)} items")
        return "list", items
    
    # Fallback: other common list keys (for flexibility with non-Zededa mocks)
    fallback_keys = ["items", "data", "results", "users", "roles", "devices", 
                     "nodes", "apps", "images", "networks", "instances", "projects", 
                     "enterprises", "brands", "datastores", "volumes", "policies"]
    
    for key in fallback_keys:
        if key in data and isinstance(data[key], list):
            items = data[key]
            # Verify it's a list of dicts (not primitives)
            if not items or all(isinstance(item, dict) for item in items):
                logger.debug(f"[MOCK] Found list at fallback key '{key}' with {len(items)} items")
                return key, items
    
    logger.warning("[MOCK] No list found in mock data (expected 'list' key)")
    return None, []


def _check_field_exists(items: list[dict], field_name: str) -> bool:
    """
    Check if a field exists in the first few items of a list.
    
    Args:
        items: List of item dictionaries
        field_name: Field name to check
    
    Returns:
        True if field exists in sample items
    """
    if not items:
        return False
    
    # Check first 3 items (or all if less than 3)
    sample_size = min(3, len(items))
    for item in items[:sample_size]:
        if field_name in item:
            return True
    
    return False


def _convert_param_to_field_name(param_name: str) -> str:
    """
    Convert parameter name to potential field name(s).
    
    Handles common naming conventions:
    - snake_case -> camelCase (e.g., run_state -> runState)
    - removes common prefixes (e.g., filter_, query_)
    
    Args:
        param_name: Parameter name from function call
    
    Returns:
        Converted field name
    
    Example:
        >>> _convert_param_to_field_name("run_state")
        "runState"
        >>> _convert_param_to_field_name("filter_name")
        "name"
    """
    # Remove common prefixes
    for prefix in ["filter_", "query_", "search_"]:
        if param_name.startswith(prefix):
            param_name = param_name[len(prefix):]
    
    # Convert snake_case to camelCase
    parts = param_name.split("_")
    if len(parts) > 1:
        return parts[0] + "".join(word.capitalize() for word in parts[1:])
    
    return param_name


def _is_pattern_filter(value: Any) -> bool:
    """
    Check if a filter value appears to be a pattern (contains wildcards).
    
    Args:
        value: Filter value to check
    
    Returns:
        True if value contains wildcards (* or ?)
    """
    return isinstance(value, str) and ("*" in value or "?" in value)


def _matches_enum_value(item_value: Any, filter_value: Any, field_name: str = "") -> bool:
    """
    Check if an item value matches a filter value, handling Zededa enum prefixes.
    
    Zededa API uses enum values with prefixes derived from field names:
    - runState: RUN_STATE_ONLINE, RUN_STATE_OFFLINE, RUN_STATE_UNKNOWN
    - adminState: ADMIN_STATE_ACTIVE, ADMIN_STATE_INACTIVE
    - swState: SW_STATE_RUNNING, SW_STATE_HALTED
    - appType: APP_TYPE_VM, APP_TYPE_CONTAINER
    - originType: ORIGIN_TYPE_LOCAL, ORIGIN_TYPE_GLOBAL
    - deploymentType: DEPLOYMENT_TYPE_STAND_ALONE, DEPLOYMENT_TYPE_K3S
    
    This function matches:
    1. Exact match: "RUN_STATE_ONLINE" == "RUN_STATE_ONLINE"
    2. Suffix match: "ONLINE" matches "RUN_STATE_ONLINE"
    3. Prefix-derived match: For field "runState", "ONLINE" matches "RUN_STATE_ONLINE"
    
    Args:
        item_value: Value from the mock data item
        filter_value: Value from the filter parameter
        field_name: The field name being filtered (used to derive prefix)
    
    Returns:
        True if values match (exact, suffix, or prefix-derived match)
    """
    if item_value is None or filter_value is None:
        return item_value == filter_value
    
    # Convert to strings for comparison
    item_str = str(item_value).upper()
    filter_str = str(filter_value).upper()
    
    # Exact match (case-insensitive)
    if item_str == filter_str:
        return True
    
    # Suffix match: "RUN_STATE_ONLINE" ends with "_ONLINE"
    if item_str.endswith(f"_{filter_str}"):
        return True
    
    # Reverse suffix match: filter "RUN_STATE_ONLINE" matches item "ONLINE"
    if filter_str.endswith(f"_{item_str}"):
        return True
    
    # Derive prefix from field name and try prefix + filter_value
    # e.g., field "runState" -> prefix "RUN_STATE_", so "ONLINE" becomes "RUN_STATE_ONLINE"
    if field_name:
        # Convert camelCase to UPPER_SNAKE_CASE prefix
        # runState -> RUN_STATE_, adminState -> ADMIN_STATE_, appType -> APP_TYPE_
        prefix = _field_name_to_enum_prefix(field_name)
        if prefix:
            derived_value = f"{prefix}{filter_str}"
            if item_str == derived_value:
                return True
    
    return False


def _field_name_to_enum_prefix(field_name: str) -> str:
    """
    Convert a camelCase field name to its corresponding UPPER_SNAKE_CASE enum prefix.
    
    Examples:
        runState -> RUN_STATE_
        adminState -> ADMIN_STATE_
        swState -> SW_STATE_
        appType -> APP_TYPE_
        originType -> ORIGIN_TYPE_
        deploymentType -> DEPLOYMENT_TYPE_
    
    Args:
        field_name: camelCase field name
    
    Returns:
        UPPER_SNAKE_CASE prefix with trailing underscore, or empty string if no conversion
    """
    import re
    
    if not field_name:
        return ""
    
    # Convert camelCase to UPPER_SNAKE_CASE
    # Insert underscore before uppercase letters, then uppercase everything
    snake_case = re.sub(r'([a-z])([A-Z])', r'\1_\2', field_name)
    return snake_case.upper() + "_"


def filter_mock_list(
    mock_data: dict[str, Any],
    page_size: Optional[int] = None,
    page_num: Optional[int] = 1,
    **filters  # ALL filters as kwargs - completely generic!
) -> dict[str, Any]:
    """
    Universally filter mock list data based on ANY query parameters.
    
    This is a FULLY GENERIC filter function that works with any MCP tool
    without needing predefined parameters. It automatically:
    1. Detects which filters match fields in the data
    2. Applies appropriate filtering (exact match or pattern)
    3. Handles pagination
    4. Updates metadata
    
    Magic Features:
    - Auto-converts parameter names (snake_case -> camelCase)
    - Detects pattern filters automatically (contains * or ?)
    - Tries multiple field name variations (name, title, etc.)
    - Only applies filters for fields that exist
    - Fully introspective - no hardcoded assumptions
    
    Args:
        mock_data: The mock data dictionary
        page_size: Number of items per page (pagination)
        page_num: Page number, 1-indexed (pagination)
        **filters: ANY filter parameters as keyword arguments
                   Examples: name="prod-1", run_state="ONLINE", 
                            name_pattern="prod-*", status="active"
    
    Returns:
        Filtered mock data dictionary with updated list and metadata
    
    Examples:
        >>> # Works with ANY parameters - no predefinition needed!
        >>> filter_mock_list(mock_data, run_state="ONLINE")
        >>> filter_mock_list(mock_data, name_pattern="prod-*", project_name="production")
        >>> filter_mock_list(mock_data, status="active", type="gateway", region="us-west")
        >>> filter_mock_list(mock_data, custom_field_123="value")  # Any field!
    
    How it works:
        1. Extracts list from mock_data (auto-detects location)
        2. For each filter parameter:
           a. Tries parameter name as-is
           b. Tries camelCase conversion (run_state -> runState)
           c. For "name" filters, also tries "title" field
           d. Only applies if field exists in data
        3. Detects pattern filters (* or ?) automatically
        4. Applies pagination
        5. Updates metadata
    """
    # Find the list in the data structure
    list_key, items = _find_list_in_data(mock_data)
    
    if not list_key:
        logger.warning("[MOCK] No list found in mock data, returning unchanged")
        return mock_data
    
    if not items:
        logger.info("[MOCK] Empty list in mock data, no filtering needed")
        return mock_data
    
    original_count = len(items)
    filtered_items = items.copy()
    filters_applied = []
    
    # Comprehensive parameter-to-field mapping
    # Generated from analysis of all MCP tools and mock data structures
    # This maps filter parameter names to actual field names in API responses
    FILTER_PARAMETER_MAPPINGS = {
        # Name-related parameters
        "name": ["name"],
        "name_value": ["name"],
        "name_pattern": ["name"],
        "device_name": ["name", "deviceName"],
        "app_name": ["name", "appName"],
        "project_name": ["projectName"],
        "project_name_pattern": ["projectName"],
        "image_name": ["name", "imageName"],
        "brand_name": ["name", "brandName"],
        "model_name": ["name", "modelName"],
        "cluster_name": ["name", "clusterName"],
        "network_name": ["name", "networkName"],
        "role_name": ["roleName", "name"],
        "username": ["username", "name"],
        
        # State-related parameters
        "run_state": ["runState"],
        "admin_state": ["adminState"],
        "sw_state": ["swState"],
        "state": ["state", "runState", "adminState"],
        "status": ["status", "runState", "state"],
        
        # Type-related parameters
        "app_type": ["appType"],
        "deployment_type": ["deploymentType"],
        "image_type": ["imageType"],
        "device_type": ["deviceType"],
        "datastore_type": ["type", "datastoreType"],
        "ds_type": ["dsType", "type"],
        "artifact_type": ["type", "artifactType"],
        "type": ["type", "appType", "imageType"],
        "cluster_type": ["type", "clusterType"],
        "integration_type": ["integrationType", "type"],
        
        # ID-related parameters
        "id": ["id"],
        "device_id": ["deviceId", "id"],
        "app_id": ["appId", "id"],
        "project_id": ["projectId", "id"],
        "image_id": ["imageId", "id"],
        "cluster_id": ["clusterId", "id"],
        "brand_id": ["brandId", "id"],
        "datastore_id": ["datastoreId", "id"],
        
        # Version-related parameters
        "user_defined_version": ["userDefinedVersion"],
        "eve_image_version": ["eveImageName", "eveImageVersion"],
        "image_version": ["imageVersion", "version"],
        "bundle_version": ["bundleVersion"],
        
        # Boolean/feature flags
        "is_eve_latest": ["isEveLatest"],
        "remote_console": ["remoteConsole"],
        "enable_vnc": ["enablevnc"],
        "is_imported": ["isImported"],
        "enterprise_default": ["enterpriseDefault"],
        "device_default": ["deviceDefault"],
        
        # Architecture/platform
        "machine_arch": ["machineArch"],
        "cpu_arch": ["cpuArch"],
        "platform": ["platform"],
        "arch": ["arch", "machineArch", "cpuArch"],
        "image_arch": ["arch", "imageArch"],
        
        # Location/region
        "location": ["location"],
        "region": ["region"],
        
        # Tags/labels
        "tags": ["tags"],
        "labels": ["labels"],
        "label_name": ["labels", "tags"],
        
        # Counts/metrics
        "app_inst_count": ["appInstCount"],
        "load": ["load"],
        
        # EVE-specific
        "eve_lts_support_type": ["eveLtsSupportType"],
        "eve_image_name": ["eveImageName"],
        
        # Serial/hardware
        "serial_no": ["serialNo"],
        "serial": ["serialNo", "serial"],
        
        # Network
        "ip_address": ["ipAddress", "ip"],
        
        # Image format
        "image_format": ["format", "imageFormat"],
        
        # Project patterns
        "filter_project_name": ["projectName"],
        "filter_project_name_pattern": ["projectName"],
        "filter_name_pattern": ["name"],
        
        # Patch envelope
        "patch_envelope_name": ["patchEnvelopeName"],
        "patch_envelope_name_pattern": ["patchEnvelopeName"],
        
        # App instance specific
        "app_inst_name": ["name", "appInstName"],
        "app_bundle_name": ["appName", "name"],
        
        # Volume instance specific
        "device_name_pattern": ["deviceName", "name"],
        "project_name_pattern": ["projectName"],
        
        # Origin type
        "origin_type": ["originType"],
        
        # Category
        "category": ["category"],
        "app_category": ["category", "appCategory"],
        
        # Title pattern
        "title_pattern": ["title"],
    }
    
    # Process each filter parameter
    for param_name, filter_value in filters.items():
        if filter_value is None:
            continue
        
        # Determine if this is a pattern filter
        is_pattern = _is_pattern_filter(filter_value)
        
        # Generate candidate field names to try
        candidate_fields = []
        
        # Check if this parameter has a predefined mapping
        if param_name in FILTER_PARAMETER_MAPPINGS:
            candidate_fields.extend(FILTER_PARAMETER_MAPPINGS[param_name])
        else:
            # Try the parameter name as-is
            candidate_fields.append(param_name)
            # Try camelCase conversion
            camel_case = _convert_param_to_field_name(param_name)
            if camel_case != param_name:
                candidate_fields.append(camel_case)
        
        # Try to apply the filter with each candidate field name
        filter_applied = False
        for field_name in candidate_fields:
            # Check if this field exists in the data
            if not _check_field_exists(filtered_items, field_name):
                continue
            
            # Apply the filter
            before_count = len(filtered_items)
            
            if is_pattern:
                # Pattern matching with wildcards
                regex_pattern = str(filter_value).replace("*", ".*").replace("?", ".")
                regex = re.compile(f"^{regex_pattern}$", re.IGNORECASE)
                filtered_items = [
                    item for item in filtered_items 
                    if regex.match(str(item.get(field_name, "")))
                ]
                if len(filtered_items) != before_count:
                    filters_applied.append(f"{field_name}~{filter_value}")
                    logger.debug(f"[MOCK] Applied pattern filter {field_name}~{filter_value}: {before_count} -> {len(filtered_items)} items")
                    filter_applied = True
                    break  # Success - don't try other candidate fields
            else:
                # Exact matching with enum prefix support
                # This handles Zededa API enum values like RUN_STATE_ONLINE, ADMIN_STATE_ACTIVE, etc.
                # Pass field_name to derive the expected enum prefix
                filtered_items = [
                    item for item in filtered_items 
                    if _matches_enum_value(item.get(field_name), filter_value, field_name)
                ]
                if len(filtered_items) != before_count:
                    filters_applied.append(f"{field_name}={filter_value}")
                    logger.debug(f"[MOCK] Applied filter {field_name}={filter_value}: {before_count} -> {len(filtered_items)} items")
                    filter_applied = True
                    break  # Success - don't try other candidate fields
        
        if not filter_applied:
            logger.debug(f"[MOCK] Skipping filter {param_name}={filter_value} (no matching field found in data)")
    
    # Apply pagination
    paginated_items = filtered_items
    if page_size and page_size > 0:
        page_num = max(1, page_num or 1)  # Ensure page_num is at least 1
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = filtered_items[start_idx:end_idx]
        logger.debug(f"[MOCK] Paginated: page {page_num}, size {page_size}, showing {len(paginated_items)}/{len(filtered_items)} items")
    
    # Create result with filtered data
    result = mock_data.copy()
    result[list_key] = paginated_items
    
    # Update Zededa API standard pagination metadata
    # All Zededa list responses have "next" with pagination info
    if "next" in result and isinstance(result["next"], dict):
        result["next"] = result["next"].copy()
        # Update totalPages based on filtered items
        if page_size and page_size > 0:
            total_pages = (len(filtered_items) + page_size - 1) // page_size  # Ceiling division
            result["next"]["totalPages"] = total_pages
            result["next"]["pageSize"] = page_size
            result["next"]["pageNum"] = page_num or 1
        # Note: We don't update totalCount in "next" as Zededa API doesn't have it there
        # totalCount is a separate top-level field in some responses
    
    # Update totalCount if present (some Zededa responses have this)
    if "totalCount" in result:
        result["totalCount"] = len(filtered_items)
    
    # Log summary
    filter_summary = f" with filters: {', '.join(filters_applied)}" if filters_applied else " (no filters applied)"
    logger.info(
        f"[MOCK] Filtered list{filter_summary}: "
        f"{original_count} -> {len(filtered_items)} items "
        f"(showing {len(paginated_items)})"
    )
    
    return result


def _is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID format.
    
    Supports UUID v1-v5 formats with or without hyphens.
    
    Args:
        value: String to check
    
    Returns:
        True if the string is a valid UUID format
    
    Examples:
        >>> _is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> _is_valid_uuid("my-device-name")
        False
    """
    if not value or not isinstance(value, str):
        return False
    
    # UUID pattern: 8-4-4-4-12 hex characters with optional hyphens
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def _looks_like_id(identifier: str) -> bool:
    """
    Intelligently determine if an identifier looks like an ID vs a name.
    
    This uses multiple heuristics to make the best guess:
    1. Check for UUID format (most common ID format in Zededa)
    2. Check for numeric-only strings
    3. Check for hash-like patterns (long hex strings)
    4. Names typically have readable characters, spaces, or descriptive patterns
    
    Args:
        identifier: The identifier string to analyze
    
    Returns:
        True if the identifier appears to be an ID, False if it looks like a name
    
    Examples:
        >>> _looks_like_id("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> _looks_like_id("my-production-server")
        False
        >>> _looks_like_id("abc123def456")  # Long hex string
        True
        >>> _looks_like_id("server-01")
        False
    """
    if not identifier or not isinstance(identifier, str):
        return False
    
    identifier = identifier.strip()
    
    # Check for UUID format (most reliable indicator)
    if _is_valid_uuid(identifier):
        logger.debug(f"[MOCK] Identifier '{identifier}' detected as UUID format")
        return True
    
    # Check for pure numeric ID
    if identifier.isdigit():
        logger.debug(f"[MOCK] Identifier '{identifier}' detected as numeric ID")
        return True
    
    # Check for long hex-like strings (likely hash or ID)
    # At least 16 characters and only hex characters
    if len(identifier) >= 16 and re.match(r'^[0-9a-f]+$', identifier, re.IGNORECASE):
        logger.debug(f"[MOCK] Identifier '{identifier}' detected as hex hash/ID")
        return True
    
    # Check for base64-like encoded IDs (common in some systems)
    # These are typically long strings without common word patterns
    if len(identifier) >= 20 and re.match(r'^[A-Za-z0-9+/=]+$', identifier) and ' ' not in identifier:
        # But exclude things that look like readable names
        if not re.search(r'[aeiou]{2,}', identifier, re.IGNORECASE):  # No vowel clusters = likely ID
            logger.debug(f"[MOCK] Identifier '{identifier}' detected as base64-like ID")
            return True
    
    # Default: treat as a name
    logger.debug(f"[MOCK] Identifier '{identifier}' detected as human-readable name")
    return False


def filter_mock_by_identifier(
    mock_data: dict[str, Any],
    identifier: str,
    lookup_by: str = "auto",
    id_field: str = "id",
    name_field: str = "name"
) -> Union[dict[str, Any], None]:
    """
    Intelligently filter mock data by identifier, automatically determining
    whether to search by ID or name based on the identifier format.
    
    This is the recommended entry point for single-item mock filtering.
    It combines the intelligence of both filter_mock_by_id and filter_mock_by_name
    with automatic detection of the identifier type.
    
    Strategy:
    1. If lookup_by is explicitly "id" or "name", use that method directly
    2. If lookup_by is "auto", analyze the identifier to guess the best method
    3. If the first method fails, try the alternate method as fallback
    4. Return None only if both methods fail
    
    Args:
        mock_data: Mock data (could be a single item or contain a list)
        identifier: The ID or name being requested
        lookup_by: Search method:
                   - "id": Force ID-based lookup
                   - "name": Force name-based lookup  
                   - "auto": Automatically detect based on identifier format (default)
        id_field: Field name for ID in the data (default: "id")
        name_field: Field name for name in the data (default: "name")
    
    Returns:
        Matching item from mock data, or None if not found
        
    Examples:
        >>> # Auto-detect: UUID detected, searches by ID first
        >>> item = filter_mock_by_identifier(mock, "550e8400-e29b-41d4-a716-446655440000")
        
        >>> # Auto-detect: Readable name detected, searches by name first
        >>> item = filter_mock_by_identifier(mock, "my-production-server")
        
        >>> # Explicit ID lookup
        >>> item = filter_mock_by_identifier(mock, "abc123", lookup_by="id")
        
        >>> # Explicit name lookup with custom field
        >>> item = filter_mock_by_identifier(mock, "admin", lookup_by="name", name_field="username")
    """
    if not identifier:
        logger.warning("[MOCK] Empty identifier provided, returning None")
        return None
    
    identifier = str(identifier).strip()
    
    # Determine the primary lookup method
    if lookup_by == "id":
        primary_is_id = True
        logger.debug(f"[MOCK] Using explicit ID lookup for '{identifier}'")
    elif lookup_by == "name":
        primary_is_id = False
        logger.debug(f"[MOCK] Using explicit name lookup for '{identifier}'")
    else:  # "auto" or any other value
        primary_is_id = _looks_like_id(identifier)
        detected_type = "ID" if primary_is_id else "name"
        logger.info(f"[MOCK] Auto-detected identifier '{identifier}' as {detected_type}")
    
    # Try primary method first
    if primary_is_id:
        result = filter_mock_by_id(mock_data, identifier, id_field)
        if result is not None:
            return result
        # Fallback to name lookup
        logger.debug(f"[MOCK] ID lookup failed for '{identifier}', trying name lookup as fallback")
        result = filter_mock_by_name(mock_data, identifier, name_field)
        if result is not None:
            logger.info(f"[MOCK] Found '{identifier}' via name fallback (was requested as ID)")
            return result
    else:
        result = filter_mock_by_name(mock_data, identifier, name_field)
        if result is not None:
            return result
        # Fallback to ID lookup
        logger.debug(f"[MOCK] Name lookup failed for '{identifier}', trying ID lookup as fallback")
        result = filter_mock_by_id(mock_data, identifier, id_field)
        if result is not None:
            logger.info(f"[MOCK] Found '{identifier}' via ID fallback (was requested as name)")
            return result
    
    # Neither method found the item
    logger.warning(f"[MOCK] No item found for identifier '{identifier}' (tried both ID and name)")
    return None


def filter_mock_by_id(
    mock_data: dict[str, Any],
    requested_id: str,
    id_field: str = "id"
) -> Union[dict[str, Any], None]:
    """
    Filter mock data to return a specific item by ID.
    
    This mimics real API behavior: returns the matching item if found,
    or None if not found (allowing the caller to handle the error).
    
    Strategy:
    1. Check if mock_data itself is a single item with matching ID
    2. Search for a list and look for matching item within it
    3. Return None if no match (mimics API 404 behavior)
    
    Args:
        mock_data: Mock data (could be a single item or contain a list)
        requested_id: The ID being requested
        id_field: Field name for ID (default: "id", could be "userId", "deviceId", etc.)
    
    Returns:
        Filtered mock data if ID matches, None if not found
    
    Example:
        >>> item = filter_mock_by_id(mock_data, "abc-123")
        >>> if item is None:
        ...     return f"Failed to retrieve item with ID: abc-123"
    """
    # Case 1: mock_data is already a single item
    if isinstance(mock_data, dict) and id_field in mock_data:
        if mock_data[id_field] == requested_id:
            logger.info(f"[MOCK] Direct match: {id_field}={requested_id}")
            return mock_data
        else:
            # ID doesn't match the single item, try to find in list if present
            logger.debug(f"[MOCK] Single item {id_field}={mock_data.get(id_field)} doesn't match {requested_id}, checking for list")
    
    # Case 2: mock_data contains a list - search within it
    list_key, items = _find_list_in_data(mock_data)
    
    if list_key and items:
        # Check if id_field exists in the items
        if not _check_field_exists(items, id_field):
            logger.warning(f"[MOCK] Field '{id_field}' not found in list items, cannot filter by ID")
            return None
        
        # Search for matching item
        for item in items:
            if item.get(id_field) == requested_id:
                logger.info(f"[MOCK] Found item with {id_field}={requested_id} in list[{list_key}]")
                return item
    
    # Case 3: No match found
    logger.warning(f"[MOCK] No item found with {id_field}={requested_id}, returning None (mimics 404)")
    return None


def filter_mock_by_name(
    mock_data: dict[str, Any],
    requested_name: str,
    name_field: str = "name"
) -> Union[dict[str, Any], None]:
    """
    Filter mock data to return a specific item by name.
    
    This mimics real API behavior: returns the matching item if found,
    or None if not found (allowing the caller to handle the error).
    
    Strategy:
    1. Check if mock_data itself is a single item with matching name
    2. Search for a list and look for matching item within it
    3. Try alternate field names (name, title) automatically
    4. Return None if no match (mimics API 404 behavior)
    
    Args:
        mock_data: Mock data (could be a single item or contain a list)
        requested_name: The name being requested
        name_field: Primary field name for name (default: "name")
                   Will also try "title" as fallback
    
    Returns:
        Filtered mock data if name matches, None if not found
    
    Example:
        >>> item = filter_mock_by_name(mock_data, "my-device")
        >>> if item is None:
        ...     return f"Failed to retrieve item with name: my-device"
    """
    # Possible name field variations to try
    name_fields = [name_field]
    if name_field != "name" and name_field != "username":
        name_fields.append("name")
    
    # Case 1: mock_data is already a single item
    if isinstance(mock_data, dict):
        for field in name_fields:
            if field in mock_data and mock_data[field] == requested_name:
                logger.info(f"[MOCK] Direct match: {field}={requested_name}")
                return mock_data
    
    # Case 2: mock_data contains a list - search within it
    list_key, items = _find_list_in_data(mock_data)
    
    if list_key and items:
        # Try each possible name field
        for field in name_fields:
            if not _check_field_exists(items, field):
                logger.debug(f"[MOCK] Field '{field}' not found in list items, trying next...")
                continue
            
            # Search for matching item
            for item in items:
                if item.get(field) == requested_name:
                    logger.info(f"[MOCK] Found item with {field}={requested_name} in list[{list_key}]")
                    return item
    
    # Case 3: No match found
    logger.warning(f"[MOCK] No item found with name={requested_name} (tried fields: {name_fields}), returning None (mimics 404)")
    return None


def filter_mock_time_series(
    mock_data: dict[str, Any],
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    metric_type: Optional[str] = None
) -> dict[str, Any]:
    """
    Filter mock time series data based on time range and metric type.
    
    Args:
        mock_data: Mock metrics/events data
        start_time: ISO 8601 start time
        end_time: ISO 8601 end time
        metric_type: Metric type filter
    
    Returns:
        Filtered mock data
    
    Example:
        >>> filtered = filter_mock_time_series(
        ...     mock_data,
        ...     start_time="2024-01-01T00:00:00Z",
        ...     end_time="2024-01-02T00:00:00Z"
        ... )
    """
    result = mock_data.copy()
    
    # Filter data points by time if available
    if "data" in result and isinstance(result["data"], list):
        data_points = result["data"]
        original_count = len(data_points)
        
        if start_time or end_time:
            filtered_points = []
            for point in data_points:
                timestamp_str = point.get("timestamp") or point.get("time")
                if not timestamp_str:
                    filtered_points.append(point)
                    continue
                
                try:
                    point_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    
                    # Check start time
                    if start_time:
                        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        if point_time < start:
                            continue
                    
                    # Check end time
                    if end_time:
                        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                        if point_time > end:
                            continue
                    
                    filtered_points.append(point)
                except (ValueError, AttributeError):
                    # Keep points with invalid timestamps
                    filtered_points.append(point)
            
            result["data"] = filtered_points
            logger.info(
                f"[MOCK] Filtered time series: {original_count} -> {len(filtered_points)} data points"
            )
    
    # Add metadata about the filter
    if "_request_info" not in result:
        result["_request_info"] = {}
    result["_request_info"]["start_time"] = start_time
    result["_request_info"]["end_time"] = end_time
    result["_request_info"]["metric_type"] = metric_type
    
    return result


def select_mock_fields(
    mock_data: dict[str, Any],
    fields: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Select specific fields from mock data (similar to GraphQL field selection).
    
    This simulates the 'fields' parameter that some APIs support, where you can
    request only specific fields to be returned.
    
    Args:
        mock_data: Mock data dictionary or list
        fields: List of field names to keep
    
    Returns:
        Mock data with only selected fields
    
    Example:
        >>> filtered = select_mock_fields(
        ...     mock_data,
        ...     fields=["id", "name", "status"]
        ... )
    """
    if not fields:
        return mock_data
    
    def filter_item(item: dict) -> dict:
        """Filter a single item to only include specified fields."""
        if not isinstance(item, dict):
            return item
        return {k: v for k, v in item.items() if k in fields}
    
    # Handle list data
    list_key = None
    for key in ["list", "users", "roles", "devices", "nodes", "apps", "images"]:
        if isinstance(mock_data, dict) and key in mock_data:
            list_key = key
            break
    
    if list_key:
        result = mock_data.copy()
        result[list_key] = [filter_item(item) for item in mock_data[list_key]]
        logger.info(f"[MOCK] Selected fields {fields} from list items")
        return result
    elif isinstance(mock_data, dict):
        result = filter_item(mock_data)
        logger.info(f"[MOCK] Selected fields {fields} from single item")
        return result
    
    return mock_data
