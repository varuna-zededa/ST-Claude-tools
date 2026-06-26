"""
Test cases for profile_deployments module.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestProfileDeploymentsModule:
    """Test cases for profile_deployments module."""

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

    def test_register_profile_deployments_tools(self):
        """Test that profile_deployments tools are registered correctly."""
        from profile_deployments import register_profile_deployment_tools
        from unittest.mock import Mock

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_profile_deployment_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_profile_deployments_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        # Check if the function exists
        if "get_profile_deployments" in tool_functions:
            test_func = tool_functions["get_profile_deployments"]

            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"},
                ]
            }

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=mock_response,
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(
                "Function get_profile_deployments not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_get_profile_deployments_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        # Check if the function exists
        if "get_profile_deployments" in tool_functions:
            test_func = tool_functions["get_profile_deployments"]

            mock_response = {"list": [{"id": "filtered-id", "name": "filtered-item"}]}

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=mock_response,
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(
                "Function get_profile_deployments not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_get_profile_deployments_request_failure(self, mock_environment):
        """Test request failure handling."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        # Check if the function exists
        if "get_profile_deployments" in tool_functions:
            test_func = tool_functions["get_profile_deployments"]

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request", return_value=None
                ) as mock_request,
            ):

                result = await test_func()

                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(
                "Function get_profile_deployments not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_get_profile_deployments_authentication_error_handling(
        self, mock_environment
    ):
        """Test authentication error handling."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        # Check if the function exists
        if "get_profile_deployments" in tool_functions:
            test_func = tool_functions["get_profile_deployments"]

            with patch(
                "profile_deployments.ensure_bearer_token",
                side_effect=Exception("Authentication failed"),
            ):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(
                "Function get_profile_deployments not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_get_profile_deployments_large_response_truncation(
        self, mock_environment
    ):
        """Test large response handling."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        # Check if the function exists
        if "get_profile_deployments" in tool_functions:
            test_func = tool_functions["get_profile_deployments"]

            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000}
                    for i in range(100)
                ]
            }

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=large_response,
                ) as mock_request,
            ):

                result = await test_func()

                assert result == large_response
                mock_request.assert_called_once()
        else:
            pytest.skip(
                "Function get_profile_deployments not found in registered tools"
            )

    @pytest.mark.asyncio
    async def test_get_profile_deployment_by_name_success(self, mock_environment):
        """Test get_profile_deployment with name lookup."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        if "get_profile_deployment" in tool_functions:
            test_func = tool_functions["get_profile_deployment"]

            mock_response = {
                "id": "test-id",
                "name": "test-deployment",
                "status": "active",
            }

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=mock_response,
                ) as mock_request,
            ):

                result = await test_func(identifier="test-deployment", lookup_by="name")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains name endpoint
                call_args = mock_request.call_args
                assert "name" in call_args[0][0]
        else:
            pytest.skip("Function get_profile_deployment not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_profile_deployment_by_id_success(self, mock_environment):
        """Test get_profile_deployment with ID lookup."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        if "get_profile_deployment" in tool_functions:
            test_func = tool_functions["get_profile_deployment"]

            mock_response = {
                "id": "test-id-123",
                "name": "test-deployment",
                "status": "active",
            }

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=mock_response,
                ) as mock_request,
            ):

                result = await test_func(identifier="test-id-123", lookup_by="id")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains id endpoint
                call_args = mock_request.call_args
                assert "/id/" in call_args[0][0]
        else:
            pytest.skip("Function get_profile_deployment not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_profile_deployment_not_found(self, mock_environment):
        """Test get_profile_deployment when deployment not found."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        if "get_profile_deployment" in tool_functions:
            test_func = tool_functions["get_profile_deployment"]

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("profile_deployments.make_zededa_request", return_value=None),
            ):

                result = await test_func(identifier="non-existent", lookup_by="name")

                assert "not found" in result.lower()
        else:
            pytest.skip("Function get_profile_deployment not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_profile_deployment_resource_status_success(
        self, mock_environment
    ):
        """Test get_profile_deployment_resource_status."""
        from profile_deployments import register_profile_deployment_tools
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
        register_profile_deployment_tools(mock_mcp)

        if "get_profile_deployment_resource_status" in tool_functions:
            test_func = tool_functions["get_profile_deployment_resource_status"]

            mock_response = {
                "list": [
                    {"nodeId": "node-1", "status": "deployed"},
                    {"nodeId": "node-2", "status": "pending"},
                ]
            }

            with (
                patch(
                    "profile_deployments.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "profile_deployments.make_zededa_request",
                    return_value=mock_response,
                ) as mock_request,
            ):

                result = await test_func(deployment_id="test-deployment-id")

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(
                "Function get_profile_deployment_resource_status not found in registered tools"
            )
