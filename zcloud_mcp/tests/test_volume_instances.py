"""
Test cases for volume_instances module.
"""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestVolumeInstancesModule:
    """Test cases for volume_instances module."""

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

    def test_register_volume_instances_tools(self):
        """Test that volume_instances tools are registered correctly."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_volume_instance_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_all_volume_instances_success(
        self, mock_environment, mock_httpx_response
    ):
        """Test successful retrieval of all volume instances."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instances" in tool_functions:
            test_func = tool_functions["get_all_volume_instances"]

            mock_response_data = {
                "list": [
                    {"id": "vol1", "name": "test-volume-1", "size": "10GB"},
                    {"id": "vol2", "name": "test-volume-2", "size": "20GB"},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()

                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_volume_instances_with_filters(
        self, mock_environment, mock_httpx_response
    ):
        """Test volume instances query with filters."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instances" in tool_functions:
            test_func = tool_functions["get_all_volume_instances"]

            mock_response_data = {"list": [{"id": "vol1", "name": "filtered-volume"}]}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(page_size=10, device_name="test-device")

                assert result == mock_response_data
                mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_volume_instances_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instances" in tool_functions:
            test_func = tool_functions["get_all_volume_instances"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection error")
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "Request failed" in result

    @pytest.mark.asyncio
    async def test_get_all_volume_instances_http_error(
        self, mock_environment, mock_httpx_response
    ):
        """Test handling of HTTP errors."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instances" in tool_functions:
            test_func = tool_functions["get_all_volume_instances"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(500, text="Internal Server Error")
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert "HTTP error 500" in result

    @pytest.mark.asyncio
    async def test_get_volume_instance_by_name(
        self, mock_environment, mock_httpx_response
    ):
        """Test get volume instance by name."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance" in tool_functions:
            test_func = tool_functions["get_volume_instance"]

            mock_response_data = {"id": "vol123", "name": "test-volume", "size": "10GB"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("test-volume", lookup_by="name")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_volume_instance_by_id(
        self, mock_environment, mock_httpx_response
    ):
        """Test get volume instance by ID."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance" in tool_functions:
            test_func = tool_functions["get_volume_instance"]

            mock_response_data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "test-volume",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func(
                    "550e8400-e29b-41d4-a716-446655440000", lookup_by="id"
                )
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_volume_instance_invalid_uuid_fallback(
        self, mock_environment, mock_httpx_response
    ):
        """Test that invalid UUID falls back to name lookup."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance" in tool_functions:
            test_func = tool_functions["get_volume_instance"]

            mock_response_data = {"id": "vol123", "name": "not-a-uuid"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                # Invalid UUID should fallback to name lookup
                result = await test_func("not-a-uuid", lookup_by="id")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_volume_instance_not_found(
        self, mock_environment, mock_httpx_response
    ):
        """Test get volume instance when not found."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance" in tool_functions:
            test_func = tool_functions["get_volume_instance"]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(404, text="Volume instance not found")
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("nonexistent", lookup_by="name")
                assert "HTTP error 404" in result

    @pytest.mark.asyncio
    async def test_get_volume_instance_status(
        self, mock_environment, mock_httpx_response
    ):
        """Test get volume instance status."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance_status" in tool_functions:
            test_func = tool_functions["get_volume_instance_status"]

            mock_response_data = {
                "id": "vol123",
                "name": "test-volume",
                "status": "running",
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("test-volume", lookup_by="name")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_volume_instance_events(
        self, mock_environment, mock_httpx_response
    ):
        """Test get volume instance events."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_volume_instance_events" in tool_functions:
            test_func = tool_functions["get_volume_instance_events"]

            mock_response_data = {
                "list": [
                    {"timestamp": "2024-01-01", "event": "created"},
                    {"timestamp": "2024-01-02", "event": "started"},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func("test-volume", lookup_by="name")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_all_volume_instance_status(
        self, mock_environment, mock_httpx_response
    ):
        """Test get all volume instance status."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instance_status" in tool_functions:
            test_func = tool_functions["get_all_volume_instance_status"]

            mock_response_data = {
                "list": [
                    {"id": "vol1", "status": "running"},
                    {"id": "vol2", "status": "stopped"},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_get_all_volume_instance_status_config(
        self, mock_environment, mock_httpx_response
    ):
        """Test get all volume instance status and config."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instance_status_config" in tool_functions:
            test_func = tool_functions["get_all_volume_instance_status_config"]

            mock_response_data = {
                "list": [
                    {"id": "vol1", "status": "running", "config": {"size": "10GB"}},
                    {"id": "vol2", "status": "stopped", "config": {"size": "20GB"}},
                ]
            }

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
            ):

                result = await test_func()
                assert result == mock_response_data

    async def test_get_all_volume_instance_status_with_plot(
        self, mock_environment, mock_httpx_response
    ):
        """Test get all volume instance status with plot enabled."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instance_status" in tool_functions:
            test_func = tool_functions["get_all_volume_instance_status"]

            mock_response_data = {
                "list": [
                    {"id": "vol1", "status": "running"},
                    {"id": "vol2", "status": "stopped"},
                ]
            }

            mock_plot_response = {
                "data": mock_response_data,
                "plot_instructions": "some instructions",
            }

            mock_create_plot = Mock(return_value=mock_plot_response)

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
                patch(
                    "volume_instances.create_plot_response_structure", mock_create_plot
                ),
            ):

                result = await test_func(create_plot=True)
                assert result == mock_plot_response
                mock_create_plot.assert_called_once()

    async def test_get_all_volume_instance_status_config_with_plot(
        self, mock_environment, mock_httpx_response
    ):
        """Test get all volume instance status config with plot enabled."""
        from volume_instances import register_volume_instance_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_volume_instance_tools(mock_mcp)

        if "get_all_volume_instance_status_config" in tool_functions:
            test_func = tool_functions["get_all_volume_instance_status_config"]

            mock_response_data = {
                "list": [
                    {"id": "vol1", "status": "running", "config": {"size": "10GB"}},
                    {"id": "vol2", "status": "stopped", "config": {"size": "20GB"}},
                ]
            }

            mock_plot_response = {
                "data": mock_response_data,
                "plot_instructions": "some instructions",
            }

            mock_create_plot = Mock(return_value=mock_plot_response)

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=mock_httpx_response(200, mock_response_data)
            )

            with (
                patch(
                    "volume_instances.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("httpx.AsyncClient", return_value=mock_client),
                patch(
                    "volume_instances.create_plot_response_structure", mock_create_plot
                ),
            ):

                result = await test_func(create_plot=True)
                assert result == mock_plot_response
                mock_create_plot.assert_called_once()
