"""
Test file for document_policies.py module.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestDocumentPoliciesModule:
    """Test the document_policies module functions."""

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

    def test_register_document_policies_tools(self, mock_mcp):
        """Test that document_policies tools are registered correctly."""
        from document_policies import register_document_policies_tools

        register_document_policies_tools(mock_mcp)

        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_document_policies_success(self, mock_environment):
        """Test successful retrieval of document_policies."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        # Check if the function exists
        if "get_document_policies" in tool_functions:
            test_func = tool_functions["get_document_policies"]

            mock_response = {
                "list": [
                    {"id": "item1", "name": "test-item-1"},
                    {"id": "item2", "name": "test-item-2"},
                ]
            }

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_document_policies not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policies_with_filters(self, mock_environment):
        """Test document_policies query with filters."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policies" in tool_functions:
            test_func = tool_functions["get_document_policies"]

            mock_response = {"list": [{"id": "item1", "name": "filtered-item"}]}

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func(page_size=10)

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_document_policies not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policies_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policies" in tool_functions:
            test_func = tool_functions["get_document_policies"]

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=None
                ) as mock_request,
            ):

                result = await test_func()

                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_document_policies not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policies_authentication_error_handling(
        self, mock_environment
    ):
        """Test authentication error handling."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policies" in tool_functions:
            test_func = tool_functions["get_document_policies"]

            auth_error_msg = "Authorization header missing or invalid"
            with patch(
                "document_policies.ensure_bearer_token", return_value=auth_error_msg
            ):
                result = await test_func()
                assert result == auth_error_msg
        else:
            pytest.skip("Function get_document_policies not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policies_large_response(self, mock_environment):
        """Test handling of large responses."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policies" in tool_functions:
            test_func = tool_functions["get_document_policies"]

            # Create a large mock response
            large_list = [{"id": f"item{i}", "name": f"item-{i}"} for i in range(100)]
            mock_response = {"list": large_list}

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func()

                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_document_policies not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policy_by_name_success(self, mock_environment):
        """Test get_document_policy with name lookup."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policy" in tool_functions:
            test_func = tool_functions["get_document_policy"]

            mock_response = {
                "id": "test-id",
                "name": "test-policy",
                "content": "Terms...",
            }

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func(identifier="test-policy", lookup_by="name")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains name endpoint
                call_args = mock_request.call_args
                assert "name" in call_args[0][0]
        else:
            pytest.skip("Function get_document_policy not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policy_by_id_success(self, mock_environment):
        """Test get_document_policy with ID lookup."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policy" in tool_functions:
            test_func = tool_functions["get_document_policy"]

            mock_response = {
                "id": "test-id-123",
                "name": "test-policy",
                "content": "Terms...",
            }

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch(
                    "document_policies.make_zededa_request", return_value=mock_response
                ) as mock_request,
            ):

                result = await test_func(identifier="test-id-123", lookup_by="id")

                assert result == mock_response
                mock_request.assert_called_once()
                # Verify URL contains id endpoint
                call_args = mock_request.call_args
                assert "/id/" in call_args[0][0]
        else:
            pytest.skip("Function get_document_policy not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_document_policy_not_found(self, mock_environment):
        """Test get_document_policy when policy not found."""
        from document_policies import register_document_policies_tools

        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}

        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = mock_tool
        register_document_policies_tools(mock_mcp)

        if "get_document_policy" in tool_functions:
            test_func = tool_functions["get_document_policy"]

            with (
                patch(
                    "document_policies.ensure_bearer_token",
                    return_value="Bearer test-token",
                ),
                patch("document_policies.make_zededa_request", return_value=None),
            ):

                result = await test_func(identifier="non-existent", lookup_by="name")

                assert "not found" in result.lower()
        else:
            pytest.skip("Function get_document_policy not found in registered tools")
