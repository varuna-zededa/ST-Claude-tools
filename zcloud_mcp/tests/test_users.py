"""
Test cases for users module.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestUsersModule:
    """Test cases for users module."""

    @pytest.fixture
    def mock_httpx_response(self):
        """Create a mock httpx response."""

        def _create_mock(status_code=200, json_data=None, text=""):
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = text
            mock_response.json.return_value = json_data or {}
            mock_response.raise_for_status = Mock()

            if status_code >= 400:
                error = httpx.HTTPStatusError(
                    message=f"HTTP {status_code}",
                    request=Mock(),
                    response=mock_response,
                )
                mock_response.raise_for_status.side_effect = error

            return mock_response

        return _create_mock

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict(
            "os.environ",
            {
                "ZEDCLOUD_API_BEARER_TOKEN": "test-token",
                "ZEDCLOUD_API_BASE_URL": "https://api.zedcloud.local",
            },
        ):
            yield

    def test_register_users_tools(self):
        """Test that users tools are registered correctly."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_user_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_all_users_success(self, mock_environment, mock_httpx_response):
        """Test successful retrieval of all users."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_all_users" in tool_functions:
            test_func = tool_functions["get_all_users"]

            mock_response_data = {
                "list": [
                    {"id": "user1", "name": "test-user-1", "email": "user1@test.com"},
                    {"id": "user2", "name": "test-user-2", "email": "user2@test.com"},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()

                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_users_with_filters(
        self, mock_environment, mock_httpx_response
    ):
        """Test users query with filters."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_all_users" in tool_functions:
            test_func = tool_functions["get_all_users"]

            mock_response_data = {"list": [{"id": "user1", "name": "filtered-user"}]}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(page_size=10)

                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_users_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_all_users" in tool_functions:
            test_func = tool_functions["get_all_users"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection error")
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "Request failed" in result

    @pytest.mark.asyncio
    async def test_get_all_users_http_error(
        self, mock_environment, mock_httpx_response
    ):
        """Test handling of HTTP errors."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_all_users" in tool_functions:
            test_func = tool_functions["get_all_users"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(500, text="Internal Server Error")
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "HTTP error 500" in result

    @pytest.mark.asyncio
    async def test_get_user_by_name(self, mock_environment, mock_httpx_response):
        """Test get user by name."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user" in tool_functions:
            test_func = tool_functions["get_user"]

            mock_response_data = {
                "id": "user123",
                "name": "testuser",
                "email": "test@example.com",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("testuser", lookup_by="name")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_environment, mock_httpx_response):
        """Test get user by ID."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user" in tool_functions:
            test_func = tool_functions["get_user"]

            mock_response_data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "testuser",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(
                    "550e8400-e29b-41d4-a716-446655440000", lookup_by="id"
                )
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_user_invalid_uuid_fallback(
        self, mock_environment, mock_httpx_response
    ):
        """Test that invalid UUID falls back to name lookup."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user" in tool_functions:
            test_func = tool_functions["get_user"]

            mock_response_data = {"id": "user123", "name": "not-a-uuid"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                # Invalid UUID should fallback to name lookup
                result = await test_func("not-a-uuid", lookup_by="id")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_environment, mock_httpx_response):
        """Test get user when not found."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user" in tool_functions:
            test_func = tool_functions["get_user"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(404, text="User not found")
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("nonexistent", lookup_by="name")
                assert "HTTP error 404" in result

    @pytest.mark.asyncio
    async def test_get_user_self(self, mock_environment, mock_httpx_response):
        """Test get current user's own information."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user_self" in tool_functions:
            test_func = tool_functions["get_user_self"]

            mock_response_data = {
                "id": "current-user",
                "name": "me",
                "email": "me@example.com",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_user_self_forbidden(self, mock_environment, mock_httpx_response):
        """Test get user self when access is forbidden."""
        from users import register_user_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_user_tools(mock_mcp)

        if "get_user_self" in tool_functions:
            test_func = tool_functions["get_user_self"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(403, text="Access denied")
            )

            with (
                patch("users.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "Access denied" in result
