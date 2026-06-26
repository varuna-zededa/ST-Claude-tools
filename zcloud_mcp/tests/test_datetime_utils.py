"""
Test file for datetime_utils.py module.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime_utils import register_datetime_tools


class TestGetCurrentDatetime:
    """Test the get_current_datetime tool."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = Mock()
        captured_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                captured_functions[func.__name__] = func
                return func
            return decorator

        mcp.tool = mock_tool
        register_datetime_tools(mcp)
        return captured_functions

    @pytest.mark.asyncio
    async def test_get_current_datetime_no_offset(self, mock_mcp):
        """Test get_current_datetime with no offset returns current time."""
        func = mock_mcp['get_current_datetime']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone

            result = await func()

            assert result['iso_8601'] == '2025-01-15T14:30:00Z'
            assert result['timezone'] == 'UTC'
            assert result['offset_applied'] == 'none'
            assert result['is_offset_result'] is False
            assert result['components']['year'] == 2025
            assert result['components']['month'] == 1
            assert result['components']['day'] == 15
            assert result['components']['hour'] == 14
            assert result['components']['minute'] == 30

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_hour_offset(self, mock_mcp):
        """Test get_current_datetime with hour offset."""
        func = mock_mcp['get_current_datetime']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(offset_hours=-1)

            assert result['iso_8601'] == '2025-01-15T13:30:00Z'
            assert result['is_offset_result'] is True
            assert '-1 hours' in result['offset_applied']

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_day_offset(self, mock_mcp):
        """Test get_current_datetime with day offset (yesterday)."""
        func = mock_mcp['get_current_datetime']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(offset_days=-1)

            assert result['iso_8601'] == '2025-01-14T14:30:00Z'
            assert '-1 days' in result['offset_applied']

    @pytest.mark.asyncio
    async def test_get_current_datetime_with_multiple_offsets(self, mock_mcp):
        """Test get_current_datetime with multiple offsets combined."""
        func = mock_mcp['get_current_datetime']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(offset_days=-1, offset_hours=-2, offset_minutes=-30)

            # -1 day, -2 hours, -30 minutes from 2025-01-15T14:30:00Z
            # = 2025-01-14T12:00:00Z
            assert result['iso_8601'] == '2025-01-14T12:00:00Z'
            assert '-1 days' in result['offset_applied']
            assert '-2 hours' in result['offset_applied']
            assert '-30 minutes' in result['offset_applied']

    @pytest.mark.asyncio
    async def test_get_current_datetime_unix_timestamp(self, mock_mcp):
        """Test that Unix timestamp is calculated correctly."""
        func = mock_mcp['get_current_datetime']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone

            result = await func()

            # Verify Unix timestamp is correct
            expected_unix = int(fixed_time.timestamp())
            assert result['unix_timestamp'] == expected_unix
            assert result['unix_timestamp_ms'] == expected_unix * 1000


class TestGetTimeRange:
    """Test the get_time_range tool."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = Mock()
        captured_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                captured_functions[func.__name__] = func
                return func
            return decorator

        mcp.tool = mock_tool
        register_datetime_tools(mcp)
        return captured_functions

    @pytest.mark.asyncio
    async def test_get_time_range_last_hour(self, mock_mcp):
        """Test get_time_range for last hour."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(range_type='last_hour')

            assert result['range_type'] == 'last_hour'
            assert result['end_time'] == '2025-01-15T14:30:00Z'
            assert result['start_time'] == '2025-01-15T13:30:00Z'
            assert result['duration_hours'] == 1.0
            assert result['timezone'] == 'UTC'

    @pytest.mark.asyncio
    async def test_get_time_range_last_24_hours(self, mock_mcp):
        """Test get_time_range for last 24 hours."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(range_type='last_24_hours')

            assert result['range_type'] == 'last_24_hours'
            assert result['end_time'] == '2025-01-15T14:30:00Z'
            assert result['start_time'] == '2025-01-14T14:30:00Z'
            assert result['duration_hours'] == 24.0

    @pytest.mark.asyncio
    async def test_get_time_range_today(self, mock_mcp):
        """Test get_time_range for today."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone

            result = await func(range_type='today')

            assert result['range_type'] == 'today'
            assert result['start_time'] == '2025-01-15T00:00:00Z'
            assert result['end_time'] == '2025-01-15T14:30:00Z'

    @pytest.mark.asyncio
    async def test_get_time_range_yesterday(self, mock_mcp):
        """Test get_time_range for yesterday."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(range_type='yesterday')

            assert result['range_type'] == 'yesterday'
            assert result['start_time'] == '2025-01-14T00:00:00Z'
            assert result['end_time'] == '2025-01-14T23:59:59Z'

    @pytest.mark.asyncio
    async def test_get_time_range_last_week(self, mock_mcp):
        """Test get_time_range for last week."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(range_type='last_week')

            assert result['range_type'] == 'last_week'
            assert result['start_time'] == '2025-01-08T14:30:00Z'
            assert result['end_time'] == '2025-01-15T14:30:00Z'
            assert result['duration_hours'] == 168.0  # 7 days * 24 hours

    @pytest.mark.asyncio
    async def test_get_time_range_custom(self, mock_mcp):
        """Test get_time_range with custom range."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(
                range_type='custom',
                custom_start_offset_hours=48,
                custom_end_offset_hours=24
            )

            assert result['range_type'] == 'custom'
            # 48 hours ago from Jan 15 14:30 = Jan 13 14:30
            assert result['start_time'] == '2025-01-13T14:30:00Z'
            # 24 hours ago from Jan 15 14:30 = Jan 14 14:30
            assert result['end_time'] == '2025-01-14T14:30:00Z'
            assert result['duration_hours'] == 24.0

    @pytest.mark.asyncio
    async def test_get_time_range_unknown_defaults_to_24_hours(self, mock_mcp):
        """Test that unknown range_type defaults to last_24_hours."""
        func = mock_mcp['get_time_range']

        fixed_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        with patch('datetime_utils.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            result = await func(range_type='unknown_type')

            assert 'last_24_hours' in result['range_type']
            assert result['duration_hours'] == 24.0


class TestRegisterDatetimeTools:
    """Test the tool registration function."""

    def test_register_datetime_tools_creates_tools(self):
        """Test that datetime tools are registered correctly."""
        mcp = Mock()
        registered_tools = []

        def mock_tool(tags=None):
            def decorator(func):
                registered_tools.append(func.__name__)
                return func
            return decorator

        mcp.tool = mock_tool
        register_datetime_tools(mcp)

        assert 'get_current_datetime' in registered_tools
        assert 'get_time_range' in registered_tools
        assert len(registered_tools) == 2
