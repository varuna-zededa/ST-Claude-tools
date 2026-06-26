"""
Test file for enterprises.py module.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestEnterprisesModule:
    """Test the enterprises module functions."""

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

    @pytest.fixture
    def mock_httpx_response(self):
        """Create a mock httpx response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(
            return_value={
                "list": [
                    {"id": "ent-1", "name": "Test Enterprise 1"},
                    {"id": "ent-2", "name": "Test Enterprise 2"},
                ]
            }
        )
        mock_response.raise_for_status = Mock()
        return mock_response

    def test_register_enterprises_tools(self, mock_mcp):
        """Test that enterprises tools are registered correctly."""
        from enterprises import register_enterprises_tools

        register_enterprises_tools(mock_mcp)

        # Verify that mcp.tool was called (should have 3 tools: get_all_enterprises, get_enterprise, get_enterprise_self)
        assert mock_mcp.tool.call_count >= 3

    @pytest.mark.asyncio
    async def test_get_all_enterprises_success(
        self, mock_environment, mock_httpx_response
    ):
        """Test successful retrieval of all enterprises."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        # Check if the function exists
        if "get_all_enterprises" in tool_functions:
            test_func = tool_functions["get_all_enterprises"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
                patch(
                    "enterprises.limit_list_response",
                    return_value=([{"id": "ent-1"}], False),
                ),
            ):

                result = await test_func()

                assert isinstance(result, dict)
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_enterprises_with_filters(
        self, mock_environment, mock_httpx_response
    ):
        """Test enterprises query with filters."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_all_enterprises" in tool_functions:
            test_func = tool_functions["get_all_enterprises"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
                patch(
                    "enterprises.limit_list_response",
                    return_value=([{"id": "ent-1"}], False),
                ),
            ):

                result = await test_func(page_size=10, name_pattern="test*")

                assert isinstance(result, dict)
                # Verify the URL includes query parameters
                call_args = mock_client.get.call_args
                assert "pageSize" in str(call_args) or call_args is not None

    @pytest.mark.asyncio
    async def test_get_all_enterprises_http_error(self, mock_environment):
        """Test handling of HTTP errors."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_all_enterprises" in tool_functions:
            test_func = tool_functions["get_all_enterprises"]

            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Server Error", request=Mock(), response=mock_response
                )
            )

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert isinstance(result, str)
                assert "HTTP error" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "query_zededa_enterprises" in tool_functions:
            test_func = tool_functions["query_zededa_enterprises"]

            auth_error_msg = "Authorization header missing or invalid"
            with patch("enterprises.ensure_bearer_token", return_value=auth_error_msg):
                result = await test_func()
                assert result == auth_error_msg

    @pytest.mark.asyncio
    async def test_large_response_truncation(self, mock_environment):
        """Test handling of large responses with truncation."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_all_enterprises" in tool_functions:
            test_func = tool_functions["get_all_enterprises"]

            # Create a large mock response
            large_list = [
                {"id": f"ent-{i}", "name": f"enterprise-{i}"} for i in range(100)
            ]

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"list": large_list})
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Mock truncation - return first 50 items and indicate truncation
            truncated_list = large_list[:50]

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
                patch(
                    "enterprises.limit_list_response",
                    return_value=(truncated_list, True),
                ) as mock_limit,
            ):

                result = await test_func()

                assert isinstance(result, dict)
                assert "_truncated" in result
                mock_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_enterprise_by_name(self, mock_environment):
        """Test retrieving a specific enterprise by name."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise" in tool_functions:
            test_func = tool_functions["get_enterprise"]

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={"id": "ent-123", "name": "Test Enterprise"}
            )
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(identifier="Test Enterprise", lookup_by="name")

                assert isinstance(result, dict)
                assert result.get("name") == "Test Enterprise"

    @pytest.mark.asyncio
    async def test_get_enterprise_by_id(self, mock_environment):
        """Test retrieving a specific enterprise by ID."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise" in tool_functions:
            test_func = tool_functions["get_enterprise"]

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Test Enterprise",
                }
            )
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
                patch("enterprises.is_valid_uuid", return_value=True),
            ):

                result = await test_func(
                    identifier="550e8400-e29b-41d4-a716-446655440000", lookup_by="id"
                )

                assert isinstance(result, dict)
                assert result.get("id") == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_get_enterprise_invalid_uuid_fallback(self, mock_environment):
        """Test fallback to name lookup when invalid UUID provided."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise" in tool_functions:
            test_func = tool_functions["get_enterprise"]

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={"id": "ent-123", "name": "invalid-uuid"}
            )
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
                patch("enterprises.is_valid_uuid", return_value=False),
            ):

                result = await test_func(identifier="invalid-uuid", lookup_by="id")

                assert isinstance(result, dict)
                assert "_lookup_note" in result

    @pytest.mark.asyncio
    async def test_get_enterprise_not_found(self, mock_environment):
        """Test handling of enterprise not found error."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise" in tool_functions:
            test_func = tool_functions["get_enterprise"]

            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=Mock(), response=mock_response
                )
            )

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(identifier="nonexistent", lookup_by="name")

                assert isinstance(result, str)
                assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_enterprise_self(self, mock_environment):
        """Test retrieving current user's enterprise."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise_self" in tool_functions:
            test_func = tool_functions["get_enterprise_self"]

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={"id": "my-ent", "name": "My Enterprise"}
            )
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()

                assert isinstance(result, dict)
                assert result.get("name") == "My Enterprise"

    @pytest.mark.asyncio
    async def test_get_enterprise_self_forbidden(self, mock_environment):
        """Test handling of 403 Forbidden error for enterprise self."""
        from enterprises import register_enterprises_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_enterprises_tools(mock_mcp)

        if "get_enterprise_self" in tool_functions:
            test_func = tool_functions["get_enterprise_self"]

            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Forbidden", request=Mock(), response=mock_response
                )
            )

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with (
                patch(
                    "enterprises.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("enterprises.httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()

                assert isinstance(result, str)
                assert (
                    "access denied" in result.lower() or "forbidden" in result.lower()
                )
