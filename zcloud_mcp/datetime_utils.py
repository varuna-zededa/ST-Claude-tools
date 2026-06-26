"""
Zededa MCP tools for datetime utilities.

These tools provide current time information and time range calculations
to help the LLM make accurate timestamp-based queries.
"""
from typing import Any, Optional
from datetime import datetime, timezone, timedelta
from utils import logger


def register_datetime_tools(mcp):
    """Register all datetime-related MCP tools."""
    logger.info("[TOOL] DateTime tools registered")

    @mcp.tool(tags={"specific_datetime", "utility"})
    async def get_a_specific_datetime(
        offset_hours: Optional[int] = None,
        offset_minutes: Optional[int] = None,
        offset_days: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Get a specific UTC datetime with optional time offset.

        Use this tool when you need a specific time information or need to
        calculate a time relative to now (e.g., "1 hour ago", "tomorrow").

        Args:
            offset_hours: Hours to add (positive) or subtract (negative) from current time.
                         Example: -1 for "1 hour ago", +24 for "tomorrow at this time"
            offset_minutes: Minutes to add (positive) or subtract (negative) from current time.
                           Example: -30 for "30 minutes ago"
            offset_days: Days to add (positive) or subtract (negative) from current time.
                        Example: -1 for "yesterday", -7 for "a week ago"

        Returns:
            Dictionary containing:
            - iso_8601: Current datetime in ISO 8601 format (e.g., "2025-01-15T14:30:00Z")
            - unix_timestamp: Unix timestamp in seconds
            - unix_timestamp_ms: Unix timestamp in milliseconds
            - components: Date/time components (year, month, day, hour, minute, second)
            - offset_applied: Description of offset if any was applied

        Examples:
            - get_current_datetime() -> Current time
            - get_current_datetime(offset_hours=-1) -> 1 hour ago
            - get_current_datetime(offset_days=-7) -> 7 days ago
            - get_current_datetime(offset_hours=2, offset_minutes=30) -> 2.5 hours from now
        """
        logger.info(
            f"[QUERY] get_current_datetime called with offset_hours={offset_hours}, "
            f"offset_minutes={offset_minutes}, offset_days={offset_days}"
        )

        # Get current UTC time
        current_utc = datetime.now(timezone.utc)

        # Apply offsets if provided
        total_offset = timedelta()
        offset_parts = []

        if offset_days is not None and offset_days != 0:
            total_offset += timedelta(days=offset_days)
            offset_parts.append(f"{offset_days} days")

        if offset_hours is not None and offset_hours != 0:
            total_offset += timedelta(hours=offset_hours)
            offset_parts.append(f"{offset_hours} hours")

        if offset_minutes is not None and offset_minutes != 0:
            total_offset += timedelta(minutes=offset_minutes)
            offset_parts.append(f"{offset_minutes} minutes")

        offset_description = ", ".join(offset_parts) if offset_parts else "none"
        result_time = current_utc + total_offset

        return {
            "iso_8601": result_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "unix_timestamp": int(result_time.timestamp()),
            "unix_timestamp_ms": int(result_time.timestamp() * 1000),
            "components": {
                "year": result_time.year,
                "month": result_time.month,
                "day": result_time.day,
                "hour": result_time.hour,
                "minute": result_time.minute,
                "second": result_time.second,
                "day_of_week": result_time.strftime('%A'),
                "day_of_week_num": result_time.weekday(),  # 0=Monday, 6=Sunday
            },
            "offset_applied": offset_description,
            "is_offset_result": total_offset != timedelta(),
            "timezone": "UTC"
        }

    @mcp.tool(tags={"datetime_range", "utility"})
    async def get_time_range(
        range_type: str,
        custom_start_offset_hours: Optional[float] = None,
        custom_end_offset_hours: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Get a UTC time range given the range type.

        Use this tool when you need start and end times for log queries,
        event filtering, or metric retrieval.

        Args:
            range_type: The type of time range to calculate. Options:
                       - "last_hour": Past 60 minutes
                       - "last_24_hours": Past 24 hours
                       - "today": From midnight UTC today to now
                       - "yesterday": Full previous calendar day (UTC)
                       - "last_week": Past 7 days
                       - "last_month": Past 30 days
                       - "this_week": From Monday 00:00 UTC to now
                       - "this_month": From 1st of current month to now
                       - "custom": Use custom_start_offset_hours and custom_end_offset_hours
            custom_start_offset_hours: For "custom" range_type, hours before now for start time
            custom_end_offset_hours: For "custom" range_type, hours before now for end time (usually 0)

        IMPORTANT: if the user specifies a range that's not EXACTLY found in the range_type options (i.e. three days, two hours, two weeks etc.), MAKE SURE to use the custom
        option for range_type and set custom_start_offset_hours and custom_end_offset_hours. 

        Returns:
            Dictionary containing:
            - start_time: Start of range in ISO 8601 format
            - end_time: End of range in ISO 8601 format
            - start_unix: Start time as Unix timestamp
            - end_unix: End time as Unix timestamp
            - range_type: The range type that was requested
            - duration_hours: Duration of the range in hours

        Examples:
            - get_time_range("last_hour") -> Past 60 minutes
            - get_time_range("yesterday") -> Full previous day
            - get_time_range("custom", custom_start_offset_hours=48, custom_end_offset_hours=24)
              -> From 48 hours ago to 24 hours ago
        """
        logger.info(f"[QUERY] get_time_range called with range_type={range_type}")

        now = datetime.now(timezone.utc)

        if range_type == "last_hour":
            start = now - timedelta(hours=1)
            end = now
        elif range_type == "last_24_hours":
            start = now - timedelta(hours=24)
            end = now
        elif range_type == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == "yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
        elif range_type == "last_week":
            start = now - timedelta(days=7)
            end = now
        elif range_type == "last_month":
            start = now - timedelta(days=30)
            end = now
        elif range_type == "this_week":
            # Start from Monday of current week
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        elif range_type == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == "custom":
            if custom_start_offset_hours is None:
                custom_start_offset_hours = 24  # Default to 24 hours
            if custom_end_offset_hours is None:
                custom_end_offset_hours = 0  # Default to now
            start = now - timedelta(hours=custom_start_offset_hours)
            end = now - timedelta(hours=custom_end_offset_hours)
        else:
            # Default to last 24 hours for unknown range types
            logger.warning(f"Unknown range_type '{range_type}', defaulting to last_24_hours")
            start = now - timedelta(hours=24)
            end = now
            range_type = "last_24_hours (default)"

        duration = end - start
        duration_hours = duration.total_seconds() / 3600

        return {
            "start_time": start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "end_time": end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "start_unix": int(start.timestamp()),
            "end_unix": int(end.timestamp()),
            "range_type": range_type,
            "duration_hours": round(duration_hours, 2),
            "timezone": "UTC"
        }
