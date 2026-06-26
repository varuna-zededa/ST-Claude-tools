"""
Test file for roles.py module.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestRolesModule:
    """Test the roles module functions."""

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
    def mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict("os.environ", {"ZEDCLOUD_BASE_URL": "https://api.test.com"}):
            yield

    def test_register_roles_tools(self, mock_mcp):
        """Test that roles tools are registered correctly."""
        from roles import register_roles_tools

        register_roles_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_all_roles_success(self, mock_environment, mock_httpx_response):
        """Test successful retrieval of all roles."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_all_roles" in tool_functions:
            test_func = tool_functions["get_all_roles"]

            mock_response_data = {
                "list": [
                    {"id": "role1", "name": "admin", "permissions": ["read", "write"]},
                    {"id": "role2", "name": "viewer", "permissions": ["read"]},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_roles_with_filters(
        self, mock_environment, mock_httpx_response
    ):
        """Test roles query with filters."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_all_roles" in tool_functions:
            test_func = tool_functions["get_all_roles"]

            mock_response_data = {"list": [{"id": "role1", "name": "filtered-role"}]}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(page_size=10)
                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_roles_request_failure(
        self, mock_environment, mock_httpx_response
    ):
        """Test handling of request failures."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_all_roles" in tool_functions:
            test_func = tool_functions["get_all_roles"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection error")
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "Request failed" in result

    @pytest.mark.asyncio
    async def test_get_all_roles_http_error(
        self, mock_environment, mock_httpx_response
    ):
        """Test handling of HTTP errors."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_all_roles" in tool_functions:
            test_func = tool_functions["get_all_roles"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(500, text="Internal Server Error")
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "HTTP error 500" in result

    @pytest.mark.asyncio
    async def test_get_role_by_name(self, mock_environment, mock_httpx_response):
        """Test get role by name."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role" in tool_functions:
            test_func = tool_functions["get_role"]

            mock_response_data = {
                "id": "role123",
                "name": "admin",
                "permissions": ["all"],
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("admin", lookup_by="name")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_role_by_id(self, mock_environment, mock_httpx_response):
        """Test get role by ID."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role" in tool_functions:
            test_func = tool_functions["get_role"]

            mock_response_data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "admin",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(
                    "550e8400-e29b-41d4-a716-446655440000", lookup_by="id"
                )
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_role_invalid_uuid_fallback(
        self, mock_environment, mock_httpx_response
    ):
        """Test that invalid UUID falls back to name lookup."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role" in tool_functions:
            test_func = tool_functions["get_role"]

            mock_response_data = {"id": "role123", "name": "not-a-uuid"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                # Invalid UUID should fallback to name lookup
                result = await test_func("not-a-uuid", lookup_by="id")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_role_not_found(self, mock_environment, mock_httpx_response):
        """Test get role when not found."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role" in tool_functions:
            test_func = tool_functions["get_role"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(404, text="Role not found")
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("nonexistent", lookup_by="name")
                assert "HTTP error 404" in result

    @pytest.mark.asyncio
    async def test_get_role_self(self, mock_environment, mock_httpx_response):
        """Test get current user's role information."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role_self" in tool_functions:
            test_func = tool_functions["get_role_self"]

            mock_response_data = {
                "id": "current-role",
                "name": "admin",
                "permissions": ["all"],
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_role_self_forbidden(self, mock_environment, mock_httpx_response):
        """Test get role self when access is forbidden."""
        from roles import register_roles_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_roles_tools(mock_mcp)

        if "get_role_self" in tool_functions:
            test_func = tool_functions["get_role_self"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(403, text="Access denied")
            )

            with (
                patch("roles.ensure_bearer_token", return_value="Bearer test-token"),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "Access denied" in result
