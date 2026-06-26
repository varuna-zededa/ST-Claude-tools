"""
MCP-specific swagger schema configuration, caching, and initialization.

This module contains all ZedCloud-specific swagger configuration:
- Service endpoint mappings
- API endpoint → schema mappings
- Swagger spec fetching, caching, and initialization
- Discovery mode response builders

The generic schema parser (get_schema_structure) lives in the shared
utility package (utility.swagger_schema_utils).
"""

import json
import os
import httpx
import asyncio
from typing import Any, Optional
from pathlib import Path
from datetime import datetime
import threading
import logging

# Import generic schema parser from shared utility package
from utility.swagger_schema_utils import get_schema_structure

logger = logging.getLogger(__name__)

# Configuration
ZEDEDA_API_BASE = os.getenv("ZEDCLOUD_BASE_URL", "")
SWAGGER_REFRESH_ON_STARTUP = True
SWAGGER_RETRY_INTERVAL = 300  # Retry interval in seconds (5 minutes)
SWAGGER_MAX_RETRIES = 0  # 0 = retry indefinitely until success
SWAGGER_INIT_TIMEOUT = 600  # Max time to wait for init in seconds (10 minutes)

# In-memory cache for swagger specs with timestamps
_swagger_cache: dict[str, tuple[dict, datetime]] = {}
_swagger_source: dict[str, str] = {}  # Track source: "api" or "bundled"
_cache_lock = threading.Lock()
_startup_refresh_done = False  # Track if startup refresh has been performed
_startup_refresh_in_progress = False  # Track if background refresh is running


# Mapping of service names to their swagger API paths
# These endpoints serve the swagger/OpenAPI specs directly from ZedCloud
# URL format: /api/v1/docs/zapiservices/{service_name}.swagger.json
SERVICE_SWAGGER_ENDPOINTS = {
    "zedge_node_service": "/api/v1/docs/zapiservices/zedge_node_service.swagger.json",
    "zedge_app_service": "/api/v1/docs/zapiservices/zedge_app_service.swagger.json",
    "zedge_storage_service": "/api/v1/docs/zapiservices/zedge_storage_service.swagger.json",
    "zedge_network_service": "/api/v1/docs/zapiservices/zedge_network_service.swagger.json",
    "zedge_orchestration_service": "/api/v1/docs/zapiservices/zedge_orchestration_service.swagger.json",
    "zedge_user_service": "/api/v1/docs/zapiservices/zedge_user_service.swagger.json",
    "zedge_node_cluster_service": "/api/v1/docs/zapiservices/zedge_node_cluster_service.swagger.json",
    "zedge_diag_service": "/api/v1/docs/zapiservices/zedge_diag_service.swagger.json",
    "zedge_job_service": "/api/v1/docs/zapiservices/zedge_job_service.swagger.json",
    "zedge_kubernetes_service": "/api/v1/docs/zapiservices/zedge_kubernetes_service.swagger.json",
    "zedge_app_profile_service": "/api/v1/docs/zapiservices/zedge_app_profile_service.swagger.json",
}

# Fallback: Path to bundled swagger directory
def _find_swagger_dir() -> Path:
    """Find the bundled swagger directory as fallback."""
    # Try Docker container path
    docker_path = Path("/zededa-mcp/swagger")
    if docker_path.exists():
        return docker_path

    # Try relative to this file (local dev — mcp/utility/)
    relative_path = Path(__file__).parent.parent.parent / "app" / "swagger"
    if relative_path.exists():
        return relative_path

    # Try sibling path (Docker merged layout)
    sibling_path = Path(__file__).parent / "swagger"
    if sibling_path.exists():
        return sibling_path

    # Try standalone layout: swagger/ sits next to utility/ under project root
    standalone_path = Path(__file__).parent.parent / "swagger"
    if standalone_path.exists():
        return standalone_path

    return relative_path

SWAGGER_DIR = _find_swagger_dir()

# Mapping of API endpoints to swagger services and response schemas
API_SWAGGER_MAPPING = {
    # Edge Nodes (zedge_node_service)
    "/api/v1/devices/status": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "DeviceStatusListMsg",
        "item_schema": "DeviceStatusSummaryMsg"
    },
    "/api/v1/devices/status-config": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "DeviceStatusConfigList",
        "item_schema": "deviceStatusConfig"
    },
    "/api/v1/brands": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "SysBrands",
        "item_schema": "SysBrand"
    },
    "/api/v1/brands/global": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "SysBrands",
        "item_schema": "SysBrand"
    },
    "/api/v1/sysmodels": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "SysModels",
        "item_schema": "SysModel"
    },
    "/api/v1/sysmodels/global": {
        "service": "zedge_node_service",
        "swagger_file": "zedge_node_service.swagger.json",
        "response_schema": "SysModels",
        "item_schema": "SysModel"
    },

    # Edge Apps (zedge_app_service)
    "/api/v1/apps": {
        "service": "zedge_app_service",
        "swagger_file": "zedge_app_service.swagger.json",
        "response_schema": "Apps",
        "item_schema": "AppSummary"
    },
    "/api/v1/apps/global": {
        "service": "zedge_app_service",
        "swagger_file": "zedge_app_service.swagger.json",
        "response_schema": "Apps",
        "item_schema": "AppSummary"
    },
    "/api/v1/apps/instances/status": {
        "service": "zedge_app_service",
        "swagger_file": "zedge_app_service.swagger.json",
        "response_schema": "AppInstStatusListMsg",
        "item_schema": "AppInstStatusSummaryMsg"
    },
    "/api/v1/apps/instances/status-config": {
        "service": "zedge_app_service",
        "swagger_file": "zedge_app_service.swagger.json",
        "response_schema": "AppInstConfigStatusList",
        "item_schema": "appInstConfigStatus"
    },

    # Storage (zedge_storage_service)
    "/api/v1/apps/images": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "Images",
        "item_schema": "ImageConfig"
    },
    "/api/v1/apps/images/eve": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "Images",
        "item_schema": "ImageConfig"
    },
    "/api/v1/datastores": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "Datastores",
        "item_schema": "DatastoreInfo"
    },
    "/api/v1/volumes/instances": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "VolInstList",
        "item_schema": "VolInstShortConfig"
    },
    "/api/v1/volumes/instances/status": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "VolInstStatusListMsg",
        "item_schema": "VolInstStatusSummaryMsg"
    },
    "/api/v1/volumes/instances/status-config": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "VolInstStatusListMsg",
        "item_schema": "VolInstStatusSummaryMsg"
    },
    "/api/v1/artifacts": {
        "service": "zedge_storage_service",
        "swagger_file": "zedge_storage_service.swagger.json",
        "response_schema": "ArtifactList",
        "item_schema": "Artifact"
    },

    # Networks (zedge_network_service)
    "/api/v1/networks": {
        "service": "zedge_network_service",
        "swagger_file": "zedge_network_service.swagger.json",
        "response_schema": "NetConfigList",
        "item_schema": "NetConfig"
    },
    "/api/v1/netinsts/status-config": {
        "service": "zedge_network_service",
        "swagger_file": "zedge_network_service.swagger.json",
        "response_schema": "NetInstConfigStatusList",
        "item_schema": "NetInstConfigStatus"
    },

    # Orchestration/Projects (zedge_orchestration_service)
    "/api/v1/projects": {
        "service": "zedge_orchestration_service",
        "swagger_file": "zedge_orchestration_service.swagger.json",
        "response_schema": "Projects",
        "item_schema": "Project"
    },
    "/api/v1/projects/status": {
        "service": "zedge_orchestration_service",
        "swagger_file": "zedge_orchestration_service.swagger.json",
        "response_schema": "Projects",
        "item_schema": "Project"
    },
    "/api/v1/projects/status-config": {
        "service": "zedge_orchestration_service",
        "swagger_file": "zedge_orchestration_service.swagger.json",
        "response_schema": "Projects",
        "item_schema": "Project"
    },

    # Users/IAM (zedge_user_service)
    "/api/v1/roles": {
        "service": "zedge_user_service",
        "swagger_file": "zedge_user_service.swagger.json",
        "response_schema": "Roles",
        "item_schema": "Role"
    },
    "/api/v1/realms": {
        "service": "zedge_user_service",
        "swagger_file": "zedge_user_service.swagger.json",
        "response_schema": "Realms",
        "item_schema": "Realm"
    },
    "/api/v1/cloud/policies": {
        "service": "zedge_user_service",
        "swagger_file": "zedge_user_service.swagger.json",
        "response_schema": "DocPolicies",
        "item_schema": "DocPolicySummary"
    },

    # Edge Node Clusters (zedge_node_cluster_service)
    "/api/v1/cluster": {
        "service": "zedge_node_cluster_service",
        "swagger_file": "zedge_node_cluster_service.swagger.json",
        "response_schema": "EdgeNodeClusters",
        "item_schema": "EdgeNodeClusterConfigSummary"
    },
    "/api/v1/cluster/instances": {
        "service": "zedge_node_cluster_service",
        "swagger_file": "zedge_node_cluster_service.swagger.json",
        "response_schema": "EdgeNodeClusters",
        "item_schema": "EdgeNodeClusterConfigSummary"
    },
}


async def fetch_swagger_from_api(service_name: str) -> Optional[dict]:
    """
    Fetch swagger spec from the ZedCloud API.

    This fetches the latest swagger spec directly from the API, ensuring
    the schema is always up-to-date with the current API version.

    Args:
        service_name: Name of the service (e.g., "zedge_node_service")

    Returns:
        Swagger spec as dict, or None if fetch failed
    """
    if not ZEDEDA_API_BASE:
        logger.debug("ZEDCLOUD_BASE_URL not set, cannot fetch swagger from API")
        return None

    swagger_endpoint = SERVICE_SWAGGER_ENDPOINTS.get(service_name)
    if not swagger_endpoint:
        logger.warning(f"No swagger endpoint mapping for service: {service_name}")
        return None

    url = f"{ZEDEDA_API_BASE}{swagger_endpoint}"

    try:
        headers = {
            "Accept": "application/json",
            "User-Agent": "zededa-ai-bot/1.0"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                spec = response.json()
                logger.info(f"Successfully fetched swagger from API: {service_name}")
                return spec
            else:
                logger.warning(f"Failed to fetch swagger from API: {response.status_code} - {url}")
                return None

    except Exception as e:
        logger.warning(f"Error fetching swagger from API for {service_name}: {e}")
        return None


def load_swagger_from_bundled(swagger_filename: str) -> Optional[dict]:
    """Load swagger spec from bundled files (fallback)."""
    swagger_path = SWAGGER_DIR / swagger_filename
    if not swagger_path.exists():
        logger.debug(f"Bundled swagger file not found: {swagger_path}")
        return None
    try:
        with open(swagger_path, 'r') as f:
            logger.info(f"Loaded swagger from bundled file: {swagger_filename}")
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading bundled swagger file {swagger_filename}: {e}")
        return None


def get_swagger_spec_sync(service_name: str, swagger_filename: str) -> Optional[dict]:
    """
    Get swagger spec for a service (synchronous version).

    Priority:
    1. In-memory cache
    2. Bundled swagger files (fallback)

    Note: This synchronous version doesn't fetch from API to avoid blocking.

    Args:
        service_name: Name of the service
        swagger_filename: Fallback filename for bundled swagger

    Returns:
        Swagger spec dict or None
    """
    # Check in-memory cache (cache never expires)
    with _cache_lock:
        if service_name in _swagger_cache:
            spec, cached_time = _swagger_cache[service_name]
            logger.debug(f"Using in-memory cached swagger for {service_name}")
            return spec

    # Fall back to bundled files
    bundled = load_swagger_from_bundled(swagger_filename)
    if bundled:
        with _cache_lock:
            _swagger_cache[service_name] = (bundled, datetime.now())
        return bundled

    return None


def get_swagger_source(service_name: str) -> str:
    """Get the source of a cached swagger spec ('api', 'bundled', or 'unknown')."""
    with _cache_lock:
        return _swagger_source.get(service_name, "unknown")


def get_api_response_structure(api_endpoint: str) -> Optional[dict]:
    """
    Get the complete swagger response structure for an API endpoint.

    This is used in discovery mode - returns the schema structure so LLM
    can analyze it to find which fields contain the data it needs.

    Uses synchronous loading (cache/bundled files only).

    Args:
        api_endpoint: The API endpoint (e.g., "/api/v1/devices/status")

    Returns:
        Dictionary with complete response structure from swagger, or None if not found
    """
    mapping = API_SWAGGER_MAPPING.get(api_endpoint)
    if not mapping:
        logger.warning(f"No swagger mapping for endpoint: {api_endpoint}")
        return None

    swagger_spec = get_swagger_spec_sync(
        mapping.get("service", mapping["swagger_file"].replace(".swagger.json", "")),
        mapping["swagger_file"]
    )
    if not swagger_spec:
        return None

    item_schema = mapping.get("item_schema")
    if not item_schema:
        return None

    structure = get_schema_structure(swagger_spec, item_schema)

    # Get source for sync version (bundled since sync doesn't fetch from API)
    service_name = mapping.get("service", mapping["swagger_file"].replace(".swagger.json", ""))
    source = get_swagger_source(service_name)

    print(f"[SWAGGER DISCOVERY] Endpoint: {api_endpoint} | Service: {service_name} | Source: {source} (sync)")
    logger.info(f"Discovery query for {api_endpoint} - using swagger from {source} ({service_name})")

    return {
        "_mode": "DISCOVERY - This is the swagger schema, NOT live data",
        "_source": f"Swagger loaded from: {source} (bundled file - sync mode)",
        "_description": f"Response structure for {api_endpoint} - each item in 'list' has these fields:",
        "_next_step": "Find the field containing the data you need, then call again with return_basic_fields=true and additional_fields={\"field_name\": true}",
        "_example": "Example: additional_fields={\"someFieldName\": true}. Replace 'someFieldName' with the actual field name from the schema below.",
        "fields": structure
    }


async def initialize_swagger_cache() -> None:
    """
    Initialize swagger cache on service startup with retry logic.

    This should be called when the MCP server starts to ensure swagger specs
    are up-to-date. After an upgrade, both the MCP service and ZedCloud may
    have changed, so fetching fresh specs ensures compatibility.

    In Kubernetes environments where services start simultaneously, ZedCloud
    may not be ready immediately. This function implements:
    - Exponential backoff retry (configurable attempts and delays)
    - Graceful fallback to bundled files if API is unavailable
    - Non-blocking behavior when SWAGGER_INIT_BACKGROUND=true

    The function:
    1. Clears any stale disk cache from previous runs
    2. Fetches all swagger specs from ZedCloud API (with retries)
    3. Caches them in memory and on disk
    4. Falls back to bundled files if API is unavailable after all retries

    This is idempotent - safe to call multiple times.
    """
    global _startup_refresh_done, _startup_refresh_in_progress

    if _startup_refresh_done:
        logger.debug("Swagger cache already initialized, skipping")
        return

    if _startup_refresh_in_progress:
        logger.debug("Swagger cache initialization already in progress")
        return

    if not SWAGGER_REFRESH_ON_STARTUP:
        print("[SWAGGER] Refresh on startup is disabled (SWAGGER_REFRESH_ON_STARTUP=false)")
        logger.info("Swagger refresh on startup is disabled (SWAGGER_REFRESH_ON_STARTUP=false)")
        _startup_refresh_done = True
        return

    _startup_refresh_in_progress = True
    print(f"[SWAGGER] Initializing swagger cache from ZedCloud API: {ZEDEDA_API_BASE}")
    logger.info("Initializing swagger cache on startup...")

    # Load bundled files as immediate fallback (ensures tools work right away)
    _load_bundled_swagger_files()

    # Fetch from API with retries (may block if ZedCloud is not ready)
    await _fetch_swagger_with_retry()

    _startup_refresh_done = True
    _startup_refresh_in_progress = False
    print("[SWAGGER] Initialization complete")


def _load_bundled_swagger_files() -> int:
    """Load bundled swagger files into the cache. Returns number loaded."""
    bundled_count = 0
    for service_name in SERVICE_SWAGGER_ENDPOINTS.keys():
        swagger_filename = f"{service_name}.swagger.json"
        bundled = load_swagger_from_bundled(swagger_filename)
        if bundled:
            with _cache_lock:
                if service_name not in _swagger_cache:
                    _swagger_cache[service_name] = (bundled, datetime.now())
                    _swagger_source[service_name] = "bundled"
                    bundled_count += 1

    if bundled_count > 0:
        print(f"[SWAGGER] Loaded {bundled_count} bundled swagger specs as fallback")
        logger.info(f"Loaded {bundled_count} swagger specs from bundled files as fallback")
    return bundled_count


def initialize_swagger_cache_sync() -> None:
    """
    Synchronously load bundled swagger files and schedule background API fetch.

    This is the recommended entry point for server startup. It:
    1. Loads bundled swagger files immediately (non-blocking, fast)
    2. Schedules API fetch as a background asyncio task

    The server can start accepting requests right away with bundled specs,
    while fresh specs are fetched from ZedCloud in the background.
    """
    global _startup_refresh_done, _startup_refresh_in_progress

    if _startup_refresh_done:
        logger.debug("Swagger cache already initialized, skipping")
        return

    if _startup_refresh_in_progress:
        logger.debug("Swagger cache initialization already in progress")
        return

    if not SWAGGER_REFRESH_ON_STARTUP:
        print("[SWAGGER] Refresh on startup is disabled (SWAGGER_REFRESH_ON_STARTUP=false)")
        logger.info("Swagger refresh on startup is disabled (SWAGGER_REFRESH_ON_STARTUP=false)")
        _startup_refresh_done = True
        return

    _startup_refresh_in_progress = True
    print(f"[SWAGGER] Loading bundled swagger specs...")
    logger.info("Loading bundled swagger specs on startup...")

    _load_bundled_swagger_files()

    # Mark as done so tools can work immediately with bundled specs
    _startup_refresh_done = True
    _startup_refresh_in_progress = False
    print("[SWAGGER] Bundled swagger specs loaded, API fetch will run in background")


async def _fetch_swagger_with_retry() -> None:
    """
    Fetch swagger specs from API with retry until success.

    This handles the case where ZedCloud is not yet ready in Kubernetes
    environments where all services start simultaneously.

    Retries with a consistent interval until all specs are fetched,
    or until SWAGGER_MAX_RETRIES is reached (0 = retry indefinitely).
    """
    import random

    attempt = 0
    start_time = datetime.now()
    total_services = len(SERVICE_SWAGGER_ENDPOINTS)

    while True:
        attempt += 1
        success_count = 0
        failed_services = []

        # Check timeout
        elapsed = (datetime.now() - start_time).total_seconds()
        if SWAGGER_INIT_TIMEOUT > 0 and elapsed > SWAGGER_INIT_TIMEOUT:
            logger.warning(f"Swagger initialization timeout after {elapsed:.0f}s")
            break

        # Check max retries (0 = unlimited)
        if SWAGGER_MAX_RETRIES > 0 and attempt > SWAGGER_MAX_RETRIES:
            logger.warning(f"Swagger initialization reached max retries ({SWAGGER_MAX_RETRIES})")
            break

        if attempt == 1:
            logger.info(f"Fetching swagger specs from ZedCloud API...")
        else:
            logger.info(f"Swagger fetch retry attempt {attempt}...")

        for service_name in SERVICE_SWAGGER_ENDPOINTS.keys():
            # Skip if already cached from a previous attempt
            with _cache_lock:
                if service_name in _swagger_cache:
                    cached_spec, cached_time = _swagger_cache[service_name]
                    # Check if this is a fresh API-fetched spec (not bundled)
                    # We consider it fresh if it was cached after we started
                    if cached_time >= start_time:
                        success_count += 1
                        continue

            try:
                spec = await fetch_swagger_from_api(service_name)
                if spec:
                    with _cache_lock:
                        _swagger_cache[service_name] = (spec, datetime.now())
                        _swagger_source[service_name] = "api"
                    success_count += 1
                    print(f"[SWAGGER] ✓ Fetched: {service_name}")
                    logger.info(f"Successfully fetched swagger for {service_name}")
                else:
                    failed_services.append(service_name)
                    print(f"[SWAGGER] ✗ Failed: {service_name}")
            except Exception as e:
                failed_services.append(service_name)
                print(f"[SWAGGER] ✗ Error fetching {service_name}: {e}")
                logger.warning(f"Error fetching swagger for {service_name}: {e}")

        print(f"[SWAGGER] Progress: {success_count}/{total_services} succeeded")
        logger.info(f"Swagger fetch: {success_count}/{total_services} succeeded")

        # If all succeeded, we're done
        if success_count == total_services:
            print(f"[SWAGGER] ✓ All {total_services} swagger specs fetched successfully from API")
            logger.info("All swagger specs fetched successfully from API")
            return

        # Wait before next retry with a consistent interval
        # Add small jitter (±10%) to avoid thundering herd
        jitter = SWAGGER_RETRY_INTERVAL * 0.1 * (random.random() * 2 - 1)
        delay = SWAGGER_RETRY_INTERVAL + jitter

        print(f"[SWAGGER] Waiting {delay:.0f}s before retry (missing: {', '.join(failed_services[:3])}{'...' if len(failed_services) > 3 else ''})")
        logger.info(f"ZedCloud API not fully ready, retrying in {delay:.0f}s... (missing: {', '.join(failed_services[:3])}{'...' if len(failed_services) > 3 else ''})")
        await asyncio.sleep(delay)

    # After all retries, log final status
    with _cache_lock:
        cached_count = len(_swagger_cache)

    if cached_count < total_services:
        print(f"[SWAGGER] ⚠ Completed with {cached_count}/{total_services} specs (some from bundled files)")
        logger.warning(
            f"Swagger initialization completed with {cached_count}/{total_services} specs. "
            f"Some specs loaded from bundled files. ZedCloud API may not be fully available."
        )
    else:
        print(f"[SWAGGER] ✓ Cache ready with {cached_count} specs")
        logger.info(f"Swagger cache ready with {cached_count} specs")


async def start_background_swagger_refresh() -> None:
    """
    Start a background task to fetch swagger specs from ZedCloud API.

    This should be called after the server event loop is running (e.g. via
    FastMCP lifespan or after mcp.run() starts). It replaces bundled specs
    with fresh ones from the API without blocking server startup.
    """
    try:
        logger.info("Starting background swagger API fetch...")
        await _fetch_swagger_with_retry()
        logger.info("Background swagger API fetch complete")
    except Exception as e:
        logger.warning(f"Background swagger API fetch failed: {e}")
        logger.info("Continuing with bundled swagger specs")
