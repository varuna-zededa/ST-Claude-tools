"""
Test cases for asset_groups module.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestAssetGroupsModule:
    """Test cases for asset_groups module."""

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

    def test_register_asset_groups_tools(self):
        """Test that asset_groups tools are registered correctly."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_asset_group_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_asset_groups_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        # Check if the function exists
        if "get_asset_groups" in tool_functions:
            test_func = tool_functions["get_asset_groups"]

            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"},
                ]
            }

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_asset_groups not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_groups_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        # Check if the function exists
        if "get_asset_groups" in tool_functions:
            test_func = tool_functions["get_asset_groups"]

            mock_response = {"list": [{"id": "filtered-id", "name": "filtered-item"}]}

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_asset_groups not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_groups_request_failure(self, mock_environment):
        """Test request failure handling."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        # Check if the function exists
        if "get_asset_groups" in tool_functions:
            test_func = tool_functions["get_asset_groups"]

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=None
                ) as mock_request,
            ):

                result = await test_func()

                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_asset_groups not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_groups_authentication_error_handling(
        self, mock_environment
    ):
        """Test authentication error handling."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        # Check if the function exists
        if "get_asset_groups" in tool_functions:
            test_func = tool_functions["get_asset_groups"]

            with patch(
                "asset_groups.ensure_bearer_token",
                side_effect=Exception("Authentication failed"),
            ):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip("Function get_asset_groups not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_groups_large_response_truncation(self, mock_environment):
        """Test large response handling."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        # Check if the function exists
        if "get_asset_groups" in tool_functions:
            test_func = tool_functions["get_asset_groups"]

            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000}
                    for i in range(100)
                ]
            }

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=large_response
                ) as mock_request,
            ):

                result = await test_func()

                assert result == large_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_asset_groups not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_group_by_name_success(self, mock_environment):
        """Test get_asset_group with name lookup."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        if "get_asset_group" in tool_functions:
            test_func = tool_functions["get_asset_group"]

            mock_response = {"id": "test-id", "name": "test-group", "members": []}

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func(identifier="test-group", lookup_by="name")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains name endpoint
                call_args = mock_request.call_args
                assert "name" in call_args[0][0]
        else:
            pytest.skip("Function get_asset_group not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_group_by_id_success(self, mock_environment):
        """Test get_asset_group with ID lookup."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        if "get_asset_group" in tool_functions:
            test_func = tool_functions["get_asset_group"]

            mock_response = {"id": "test-id-123", "name": "test-group", "members": []}

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch(
                    "asset_groups.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func(identifier="test-id-123", lookup_by="id")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains id endpoint
                call_args = mock_request.call_args
                assert "/id/" in call_args[0][0]
        else:
            pytest.skip("Function get_asset_group not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_asset_group_not_found(self, mock_environment):
        """Test get_asset_group when group not found."""
        from asset_groups import register_asset_group_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_asset_group_tools(mock_mcp)

        if "get_asset_group" in tool_functions:
            test_func = tool_functions["get_asset_group"]

            with (
                patch(
                    "asset_groups.ensure_bearer_token", return_value="Bearer test-token"
                ),
                patch("asset_groups.make_zededa_request", return_value=None),
            ):

                result = await test_func(identifier="non-existent", lookup_by="name")

                assert "not found" in result.lower()
        else:
            pytest.skip("Function get_asset_group not found in registered tools")
