"""
Test file for utils.py module.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any

from utils import (
    make_zededa_request,
    format_app_instance,
    convert_time_to_seconds,
    truncate_response,
    limit_list_response,
    build_query_url
)


class TestMakeZededaRequest:
    """Test the make_zededa_request function."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test a successful API request."""
        mock_response_data = {"status": "success", "data": []}

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        with patch('utils.ZEDEDA_API_BASE', 'https://api.example.com'), \
             patch('utils._http_client.request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await make_zededa_request(
                "https://api.example.com/test",
                "GET",
                "Bearer test-token"
            )

            assert result == mock_response_data

            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "https://api.example.com/test"
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test-token"
            assert headers["User-Agent"] == "zededa-ai-bot/1.0"
            assert headers["Accept"] == "application/geo+json"

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test handling of request errors."""
        with patch('utils.ZEDEDA_API_BASE', 'https://api.example.com'), \
             patch('utils._http_client.request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Connection error")

            result = await make_zededa_request(
                "https://api.example.com/test",
                "GET",
                "Bearer test-token"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        """Test handling of HTTP status errors."""
        from httpx import HTTPStatusError, Response, Request

        mock_request_obj = Mock(spec=Request)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch('utils.ZEDEDA_API_BASE', 'https://api.example.com'), \
             patch('utils._http_client.request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = HTTPStatusError(
                "Not Found", request=mock_request_obj, response=mock_response
            )

            result = await make_zededa_request(
                "https://api.example.com/test",
                "GET",
                "Bearer test-token"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_json_decode_error(self):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None

        with patch('utils.ZEDEDA_API_BASE', 'https://api.example.com'), \
             patch('utils._http_client.request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await make_zededa_request(
                "https://api.example.com/test",
                "GET",
                "Bearer test-token"
            )

            assert result is None


class TestFormatAppInstance:
    """Test the format_app_instance function."""

    def test_format_app_instance_basic(self):
        """Test formatting a basic app instance without errors."""
        app_instance = {
            "id": "app-123",
            "name": "test-app",
            "runState": "running",
            "appType": "container",
            "deploymentType": "azure",
            "deviceId": "device-456",
            "deviceName": "test-device",
            "projectName": "test-project",
            "appName": "test-bundle"
        }
        
        result = format_app_instance(app_instance)
        
        assert "Device Id: device-456" in result
        assert "Device Name: test-device" in result
        assert "App Id: app-123" in result
        assert "App Name: test-app" in result
        assert "App Status: running" in result
        assert "App Type: container" in result
        assert "Deployment Type: azure" in result
        assert "Project Name: test-project" in result
        assert "App Bundle Name: test-bundle" in result
        assert "Error Description: No error" in result
        assert "Error Severity: No error" in result
        assert "Error Timestamp: No error" in result

    def test_format_app_instance_with_error(self):
        """Test formatting an app instance with error information."""
        app_instance = {
            "id": "app-123",
            "name": "test-app",
            "runState": "error",
            "appType": "container",
            "deploymentType": "azure",
            "deviceId": "device-456",
            "deviceName": "test-device",
            "projectName": "test-project",
            "appName": "test-bundle",
            "errInfo": [
                {
                    "description": "Container failed to start",
                    "severity": "ERROR",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            ]
        }
        
        result = format_app_instance(app_instance)
        
        assert "Error Description: Container failed to start" in result
        assert "Error Severity: ERROR" in result
        assert "Error Timestamp: 2024-01-15T10:30:00Z" in result

    def test_format_app_instance_empty_fields(self):
        """Test formatting an app instance with missing fields."""
        app_instance = {}
        
        result = format_app_instance(app_instance)
        
        assert "Device Id: " in result
        assert "App Id: " in result
        assert "App Name: " in result
        assert "Error Description: No error" in result

    def test_format_app_instance_with_partial_error_info(self):
        """Test formatting an app instance with partial error information."""
        app_instance = {
            "id": "app-123",
            "name": "test-app",
            "errInfo": [
                {
                    "description": "Partial error info"
                    # Missing severity and timestamp
                }
            ]
        }
        
        result = format_app_instance(app_instance)
        
        assert "Error Description: Partial error info" in result
        assert "Error Severity: " in result  # Should be empty string
        assert "Error Timestamp: " in result  # Should be empty string


class TestConvertTimeToSeconds:
    """Test the convert_time_to_seconds function."""

    def test_convert_unix_timestamp_digits(self):
        """Test converting a string of digits (Unix timestamp)."""
        result = convert_time_to_seconds("1642242600")
        assert result == "1642242600"

    def test_convert_unix_timestamp_float(self):
        """Test converting a float Unix timestamp."""
        result = convert_time_to_seconds("1642242600.123")
        assert result == "1642242600"

    def test_convert_iso_format_with_z(self):
        """Test converting ISO format with Z suffix."""
        iso_time = "2022-01-15T10:30:00Z"
        result = convert_time_to_seconds(iso_time)
        # The result should be a string representation of Unix timestamp
        assert result.isdigit()
        # Verify it's approximately correct (allow some variance for test execution time)
        timestamp = int(result)
        assert 1642242000 <= timestamp <= 1642243000  # Within ~15 minutes of expected

    def test_convert_iso_format_with_timezone(self):
        """Test converting ISO format with timezone offset."""
        iso_time = "2022-01-15T10:30:00+00:00"
        result = convert_time_to_seconds(iso_time)
        assert result.isdigit()
        timestamp = int(result)
        assert 1642242000 <= timestamp <= 1642243000

    def test_convert_iso_format_with_microseconds(self):
        """Test converting ISO format with microseconds."""
        iso_time = "2022-01-15T10:30:00.123456Z"
        result = convert_time_to_seconds(iso_time)
        assert result.isdigit()
        timestamp = int(result)
        assert 1642242000 <= timestamp <= 1642243000

    def test_convert_invalid_time_format(self):
        """Test with invalid time format - should return as-is."""
        invalid_time = "not-a-time"
        result = convert_time_to_seconds(invalid_time)
        assert result == "not-a-time"

    def test_convert_none_input(self):
        """Test with None input - should return as-is."""
        result = convert_time_to_seconds(None)
        assert result is None

    def test_convert_empty_string(self):
        """Test with empty string input."""
        result = convert_time_to_seconds("")
        assert result == ""

    def test_convert_float_string_with_letters(self):
        """Test with string that contains letters and numbers."""
        result = convert_time_to_seconds("123abc")
        assert result == "123abc"


class TestTruncateResponse:
    """Test the truncate_response function."""

    def test_truncate_response_short_text(self):
        """Test that short text is not truncated."""
        text = "This is a short text"
        result = truncate_response(text, max_chars=100)
        assert result == text

    def test_truncate_response_long_text(self):
        """Test that long text is truncated."""
        text = "A" * 1000
        result = truncate_response(text, max_chars=100)
        assert len(result) <= 200  # 100 chars + truncation message
        assert "[Response truncated due to size limits" in result

    def test_truncate_response_at_newline(self):
        """Test that truncation happens at newline when possible."""
        text = "Line 1\nLine 2\n" + "A" * 1000
        result = truncate_response(text, max_chars=100)
        assert "Line 1\nLine 2\n" in result
        assert "[Response truncated due to size limits" in result


class TestLimitListResponse:
    """Test the limit_list_response function."""

    def test_limit_list_response_short_list(self):
        """Test that short lists are not limited."""
        items = [1, 2, 3]
        result, was_truncated = limit_list_response(items, max_items=5)
        assert result == items
        assert was_truncated is False

    def test_limit_list_response_long_list(self):
        """Test that long lists are limited."""
        items = list(range(20))
        result, was_truncated = limit_list_response(items, max_items=5)
        assert len(result) == 5
        assert result == [0, 1, 2, 3, 4]
        assert was_truncated is True


class TestBuildQueryUrl:
    """Test the build_query_url function."""

    def test_build_query_url_no_params(self):
        """Test building URL with no parameters."""
        base_url = "https://api.example.com/test"
        result = build_query_url(base_url, {})
        assert result == base_url

    def test_build_query_url_single_param(self):
        """Test building URL with single parameter."""
        base_url = "https://api.example.com/test"
        params = {"key": "value"}
        result = build_query_url(base_url, params)
        assert result == "https://api.example.com/test?key=value"

    def test_build_query_url_multiple_params(self):
        """Test building URL with multiple parameters."""
        base_url = "https://api.example.com/test"
        params = {"key1": "value1", "key2": "value2"}
        result = build_query_url(base_url, params)
        assert "key1=value1" in result
        assert "key2=value2" in result
        assert "?" in result
        assert "&" in result

    def test_build_query_url_list_param(self):
        """Test building URL with list parameter."""
        base_url = "https://api.example.com/test"
        params = {"tags": ["tag1", "tag2"]}
        result = build_query_url(base_url, params)
        assert "tags=tag1" in result
        assert "tags=tag2" in result

    def test_build_query_url_with_encoding(self):
        """Test building URL with parameters that need encoding."""
        base_url = "https://api.example.com/test"
        params = {"query": "hello world", "time": "2024-01-01T00:00:00Z"}
        result = build_query_url(base_url, params)
        assert "query=hello%20world" in result
        assert "time=2024-01-01T00%3A00%3A00Z" in result


if __name__ == "__main__":
    pytest.main([__file__])
