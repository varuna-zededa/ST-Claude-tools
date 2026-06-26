"""
Utility functions for Zededa MCP tools.
"""

from typing import Any, Tuple
import httpx
import os
import json
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from logging_config import setup_logging
from pathlib import Path

# Setup logging
log_file_path = Path(os.path.dirname(os.path.abspath(__file__))) / "zededa_mcp.log"
logger = setup_logging(__name__, str(log_file_path))

# Constants
ZEDEDA_API_BASE = os.getenv("ZEDCLOUD_BASE_URL")
if not ZEDEDA_API_BASE:
    logger.warning("ZEDCLOUD_BASE_URL is not set — all non-mock API calls will fail")

# Shared HTTP client — one connection pool for the server's lifetime
_http_client = httpx.AsyncClient(timeout=30.0)
USER_AGENT = "zededa-ai-bot/1.0"

# Response limits to prevent token exhaustion
MAX_RESPONSE_CHARS = 8000  # Maximum characters in a tool response
MAX_ITEMS_PER_RESPONSE = 10  # Maximum items to return in list responses
TRUNCATION_MESSAGE = "\n\n[Response truncated due to size limits. Use filters or pagination for more specific results.]"


def load_mock_json(filename: str, required: bool = False) -> dict | None:
    """Load mock data from JSON file in mcp/mocks directory.

    This function tries multiple possible paths to find the mock file:
    1. Relative to the mcp directory
    2. From container root (/zededa-agent)
    3. Relative to workspace root

    Args:
        filename: Name of the JSON file to load (e.g., "user-self.json")
        required: If True, raise error when mock file is not found (for USE_MOCK_API_MCP_DATA mode)

    Returns:
        Dictionary containing the mock data, or None if file not found or error occurred

    Raises:
        FileNotFoundError: If required=True and mock file is not found
        ValueError: If required=True and mock file cannot be parsed
    """
    # Get the mcp directory path (this file is in mcp/utils.py)
    mcp_dir = Path(__file__).resolve().parent

    # Try multiple possible paths
    possible_paths = [
        # From mcp/ to mcp/mocks/
        mcp_dir / "mocks" / filename,
        # If running from container root
        Path("/zededa-agent") / "mcp" / "mocks" / filename,
    ]

    for mock_path in possible_paths:
        if mock_path.exists():
            logger.info(f"[FILE] Found mock file at: {mock_path}")
            try:
                with open(mock_path, "r") as f:
                    data = json.load(f)
                    logger.info(
                        f"[SUCCESS] Successfully loaded mock data from {filename}"
                    )
                    return data
            except Exception as e:
                error_msg = f"[FAILED] Failed to parse mock file {filename}: {e}"
                logger.error(error_msg)
                if required:
                    raise ValueError(error_msg)
                return None

    # Mock file not found
    error_msg = f"Mock file not found: {filename} (tried paths: {', '.join(str(p) for p in possible_paths)})"

    if required:
        logger.error(f"[ERROR] {error_msg}")
        raise FileNotFoundError(
            f"USE_MOCK_API_MCP_DATA is enabled but required mock file is missing: {filename}\n"
            f"Searched in: {', '.join(str(p) for p in possible_paths)}\n"
            f"Please create the mock file or disable USE_MOCK_API_MCP_DATA."
        )

    logger.warning(f"[WARNING] {error_msg}")
    return None


async def make_zededa_request(
    url: str, http_verb: str, token: str | None
) -> dict[str, Any] | None:
    """Make a request to the Zededa API with proper error handling."""
    if token is None:
        logger.error(f"Cannot make request to {url}: no auth token provided")
        return None
    if not ZEDEDA_API_BASE:
        logger.error(f"Cannot make request to {url}: ZEDCLOUD_BASE_URL is not set")
        return None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
        "Authorization": token,
    }
    try:
        response = await _http_client.request(http_verb, url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Request error - {http_verb} {url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP status error - {http_verb} {url}: {e.response.status_code}"
        )
        return None
    except Exception as e:
        logger.error(f"Unexpected error - {http_verb} {url}: {e}")
        return None


def format_app_instance(app_instance: dict[str, Any]) -> str:
    """Format app instance data for display."""
    id = app_instance.get("id", "")
    name = app_instance.get("name", "")
    status = app_instance.get("runState", "")
    type = app_instance.get("appType", "")
    deployment_type = app_instance.get("deploymentType", "")
    device_id = app_instance.get("deviceId", "")
    device_name = app_instance.get("deviceName", "")
    project_name = app_instance.get("projectName", "")
    app_name = app_instance.get("appName", "")

    # Check if there is an error
    if (
        "errInfo" in app_instance
        and app_instance["errInfo"]
        and len(app_instance["errInfo"]) > 0
    ):
        error_info = app_instance["errInfo"][0]
        if error_info is not None:
            error_description = error_info.get("description", "")
            error_severity = error_info.get("severity", "")
            error_timestamp = error_info.get("timestamp", "")
        else:
            error_description = "No error"
            error_severity = "No error"
            error_timestamp = "No error"
    else:
        error_description = "No error"
        error_severity = "No error"
        error_timestamp = "No error"

    return f"""
Device Id: {device_id}
Device Name: {device_name}
App Id: {id}
App Name: {name}
App Status: {status}
App Type: {type}
Deployment Type: {deployment_type}
Project Name: {project_name}
App Bundle Name: {app_name}
Error Description: {error_description}
Error Severity: {error_severity}
Error Timestamp: {error_timestamp}
"""


def truncate_response(response: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """Truncate response if it exceeds the maximum character limit."""
    if len(response) <= max_chars:
        return response

    truncated = response[:max_chars]
    # Try to truncate at a natural boundary (end of line)
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.8:  # Only use newline if it's not too far back
        truncated = truncated[:last_newline]

    return truncated + TRUNCATION_MESSAGE


def limit_list_response(
    items: list, max_items: int = MAX_ITEMS_PER_RESPONSE
) -> Tuple[list, bool]:
    """Limit the number of items in a list response and return if truncated."""
    if len(items) <= max_items:
        return items, False
    return items[:max_items], True


def convert_time_to_seconds(time_str: str) -> str:
    """Convert ISO 8601 time string or Unix timestamp to Unix timestamp seconds."""
    if time_str is None:
        return time_str
    try:
        # First try to parse as Unix timestamp (if it's all digits)
        if time_str.strip().isdigit():
            return time_str.strip()

        # Try to parse as float (Unix timestamp with decimals)
        try:
            float(time_str.strip())
            return str(int(float(time_str.strip())))
        except ValueError:
            pass

        # It's likely an ISO format, convert to Unix timestamp
        # Handle various ISO formats
        if "T" in time_str or "-" in time_str:
            # Replace 'Z' with '+00:00' for proper ISO format parsing
            iso_time = time_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_time)
            return str(int(dt.timestamp()))

        # If all else fails, return as-is
        return time_str

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert time '{time_str}': {e}")
        # Return as-is if conversion fails
        return time_str


def build_query_url(base_url: str, params: dict[str, Any]) -> str:
    """Build URL with properly encoded query parameters."""
    query_parts = []
    for key, value in params.items():
        if isinstance(value, list):
            # Handle multi-value parameters (collectionFormat=multi)
            for item in value:
                query_parts.append(f"{key}={urllib.parse.quote(str(item))}")
        else:
            query_parts.append(f"{key}={urllib.parse.quote(str(value))}")

    if query_parts:
        return base_url + "?" + "&".join(query_parts)
    return base_url

def is_valid_uuid(value: str) -> bool:
    """Validate if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False

def get_default_time_range(default_hours: int = 24) -> Tuple[str, str]:
    """
    Get a default time range for event and log queries.

    This utility function provides a consistent default time range across
    event and log queries. It returns timestamps for the last N hours.

    Args:
        default_hours: Number of hours to look back from now (default: 24)

    Returns:
        Tuple of (start_time, end_time) as ISO 8601 formatted strings

    Example:
        >>> start, end = get_default_time_range()
        >>> # Returns timestamps for last 24 hours
        >>> start, end = get_default_time_range(48)
        >>> # Returns timestamps for last 48 hours
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=default_hours)
    start_time = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(
        f"Applying default time range of last {default_hours} hours: "
        f"{start_time} to {end_time}"
    )
    return start_time, end_time
