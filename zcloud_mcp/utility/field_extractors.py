"""
MCP-specific field extractors and discovery mode utilities.

This module contains pre-configured JsonFieldExtractor subclasses for Zededa
MCP API responses, plus the discovery mode helpers that integrate with swagger
schema discovery.

Generic base classes and helpers live in the shared utility package
(utility.json_utils), which can be reused by other services.
"""

from typing import Any, Optional
import logging

# Import generic base class from shared utility package
from utility.json_utils import JsonFieldExtractor

logger = logging.getLogger(__name__)


def detect_list_response_mode(
    discover_schema: Optional[bool] = None,
    return_basic_fields: Optional[bool] = None,
    additional_fields: Optional[dict[str, bool]] = None
) -> tuple[bool, bool]:
    """
    Detect the response mode for list API calls based on explicit flags.

    This function implements the three-mode pattern for list operations:
    - Default mode: No flags → return complete response (all fields) - SAFEST fallback
    - Discovery mode: discover_schema=True → return 1 item with complete response for structure discovery
    - Filtered mode: return_basic_fields=True → return basic fields only (+ additional_fields if specified)

    The default returns ALL fields as a safety fallback when LLM doesn't follow the intended procedure.
    LLM should explicitly request filtered mode when it wants to optimize tokens.

    Args:
        discover_schema: If True, return 1 item with complete response for structure discovery
        return_basic_fields: If True, return only basic fields (+ additional_fields if specified) for token optimization
        additional_fields: Dictionary of additional fields to include on top of basic fields (only used when return_basic_fields=True)

    Returns:
        Tuple of (is_discovery_mode, return_complete):
        - is_discovery_mode: True if discover_schema=True (requesting structure discovery with 1 item)
        - return_complete: True if should return complete unfiltered response (default mode)

    Examples:
        >>> detect_list_response_mode()
        (False, True)  # Default mode - return complete (safe fallback)
        
        >>> detect_list_response_mode(discover_schema=True)
        (True, True)  # Discovery mode - return 1 item with complete response for discovery
        
        >>> detect_list_response_mode(return_basic_fields=True)
        (False, False)  # Filtered mode - return basic fields only
        
        >>> detect_list_response_mode(return_basic_fields=True, additional_fields={"swInfo": True})
        (False, False)  # Filtered mode - return basic fields + swInfo
    """
    is_discovery_mode = discover_schema is True
    # Return complete response if:
    # 1. Discovery mode (explicit request for structure discovery)
    # 2. Default mode (return_basic_fields not set to True) - safe fallback returns all fields
    # Only filter when LLM explicitly requests it via return_basic_fields=True
    return_complete = is_discovery_mode or (return_basic_fields is not True)
    return is_discovery_mode, return_complete


def get_swagger_schema_for_discovery(api_endpoint: str) -> Optional[dict]:
    """
    Get swagger schema structure for field discovery mode.
    
    This function should be called by tools BEFORE making any API call when
    discover_schema=True. It returns the swagger schema structure so the LLM
    can understand all available fields without making an actual API request.
    
    Args:
        api_endpoint: The API endpoint path (e.g., "/api/v1/devices/status")
        
    Returns:
        Dictionary with swagger schema structure showing all fields with types
        and descriptions, or None if schema not available.
        
    Usage in tools:
        # At the start of the tool, before any API call
        is_discovery_mode, return_complete = detect_list_response_mode(discover_schema, ...)
        if is_discovery_mode:
            schema = get_swagger_schema_for_discovery("/api/v1/devices/status")
            if schema:
                return schema  # Return immediately, no API call needed
    """
    try:
        from utility.swagger_config import get_api_response_structure, SWAGGER_DIR
        logger.info(f"Discovery mode: Looking for swagger schema for {api_endpoint}")
        logger.info(f"Swagger directory: {SWAGGER_DIR}, exists: {SWAGGER_DIR.exists()}")
        result = get_api_response_structure(api_endpoint)
        if result:
            logger.info(f"Discovery mode: Successfully retrieved swagger schema for {api_endpoint}")
        else:
            logger.warning(f"Discovery mode: No swagger schema found for {api_endpoint}")
        return result
    except ImportError as e:
        logger.error(f"swagger_config not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting swagger schema for {api_endpoint}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


# ---------------------------------------------------------------------------
# Pre-configured extractors for Zededa MCP API responses
# ---------------------------------------------------------------------------

class EdgeNodeFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for edge node status responses (status API)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "adminState", "runState",
                "projectId", "projectName", "appInstCount"
            ],
            list_key="list",
            summary_keys=[
                "summaryByState",
                "summaryByAppInstanceCount",
                "summaryByEVEDistribution"
            ]
        )


class EdgeNodeStatusConfigFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for edge node status-config responses (status-config API)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "serialNo", "projectId", "projectName",
                "eveImageName", "appInstCount", "runState", "adminState"
            ],
            list_key="list",
            summary_keys=[
                "summaryByState",
                "summaryByAppInstanceCount",
                "summaryByEVEDistribution"
            ]
        )


class EdgeAppInstanceFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for edge app instance responses (both status and status-config APIs)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "deviceId", "deviceName", "appId", "appName",
                "projectId", "projectName", "runState", "appType", "swState"
            ],
            list_key="list",
            summary_keys=[
                "summaryByState",
                "summaryByAppType",
                "summaryByPatchEnvelope"
            ]
        )


class ProjectFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for project responses."""

    def __init__(self):
        super().__init__(
            basic_fields=["id", "name", "type"],
            list_key="list",
            summary_keys=["summaryByState", "summaryByType"]
        )


class EdgeAppFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for edge app responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "description", "originType",
                "networks", "drives", "cpus", "memory", "storage",
                "appInstCount", "isImported"
            ],
            list_key="list",
            summary_keys=[
                "summaryByCategory",
                "summaryByOrigin",
                "summaryByAppType",
                "summaryByAppInstanceDistribution"
            ]
        )


class ImageFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for image responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "imageStatus", "imageType", "imageArch",
                "imageFormat", "datastoreIdList", "originType"
            ],
            list_key="list",
            summary_keys=["summary"]
        )


class DatastoreFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for datastore responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "dsType",
                "dsFQDN", "dsPath", "dsStatus", "originType", "isManaged"
            ],
            list_key="list",
            summary_keys=[
                "summaryByType",
                "summaryByCategory",
                "summaryByOrigin"
            ]
        )


class NetworkFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for network responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "projectId",
                "kind", "enterpriseDefault", "mtu", "project"
            ],
            list_key="list",
            summary_keys=[
                "summaryByKind",
                "summaryByProxy",
                "summaryByDist"
            ]
        )


class VolumeInstanceFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for volume instance responses (config API - /volumes/instances)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "type", "deviceId", "projectId"
            ],
            list_key="list",
            summary_keys=["summaryByType"]
        )


class VolumeInstanceStatusFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for volume instance status responses (status API - /volumes/instances/status)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "deviceId", "deviceName", "projectId",
                "projectName", "runState", "type", "deviceState", "progressPercentage"
            ],
            list_key="list",
            summary_keys=["summaryByState", "summaryByType"]
        )


class VolumeInstanceStatusConfigFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for volume instance status-config responses (status-config API - /volumes/instances/status-config)."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "deviceId", "deviceName", "projectId",
                "projectName", "runState", "type", "deviceState", "progressPercentage"
            ],
            list_key="list",
            summary_keys=["summaryByState", "summaryByType"]
        )


class NetworkInstanceFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for network instance responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "runState", "type", "kind", "deviceDefault",
                "deviceId", "deviceName", "projectId", "projectName"
            ],
            list_key="list",
            summary_keys=["summaryByKind", "summaryByAddressType"]
        )


class BrandFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for brand responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "state", "systemMfgName", "originType"
            ],
            list_key="list",
            summary_keys=["terse"]
        )


class ModelFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for model (sysmodel) responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "brandId", "brandName",
                "state", "type", "originType"
            ],
            list_key="list",
            summary_keys=["terse", "summaryByDeviceDistribution", "summaryByBrandDistribution"]
        )


class ArtifactFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for artifact responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "format", "state", "size", "sha256"
            ],
            list_key="list",
            summary_keys=[]
        )


class ClusterInstanceFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for cluster instance responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "projectId", "projectName",
                "clusterType", "state"
            ],
            list_key="list",
            summary_keys=[]
        )


class EdgeNodeClusterFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for edge node cluster responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "projectId", "projectName",
                "state", "clusterType"
            ],
            list_key="list",
            summary_keys=[]
        )


class RealmFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for realm responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "state", "type"
            ],
            list_key="list",
            summary_keys=[]
        )


class UserFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for user responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "username", "email", "state",
                "type", "roleId"
            ],
            list_key="list",
            summary_keys=[]
        )


class RoleFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for role responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "type", "state", "scopes"
            ],
            list_key="list",
            summary_keys=[]
        )


class EnterpriseFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for enterprise responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "title", "state", "type"
            ],
            list_key="list",
            summary_keys=[]
        )


class ApiUsageFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for API usage tracking responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "endpoint", "method", "count",
                "timestamp", "statusCode"
            ],
            list_key="list",
            summary_keys=[]
        )


class DeploymentProjectFieldExtractor(JsonFieldExtractor):
    """Pre-configured field extractor for deployment project responses."""

    def __init__(self):
        super().__init__(
            basic_fields=[
                "id", "name", "projectId", "state", "type"
            ],
            list_key="list",
            summary_keys=[]
        )
