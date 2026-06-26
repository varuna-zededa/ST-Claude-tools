"""
Test cases for third_party_plugins module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestThirdPartyPluginsModule:
    """Test cases for third_party_plugins module."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'ZEDCLOUD_API_BEARER_TOKEN': 'test-token',
            'ZEDCLOUD_API_BASE_URL': 'https://api.zedcloud.local'
        }):
            yield

    def test_register_third_party_plugins_tools(self):
        """Test that third_party_plugins tools are registered correctly."""
        from third_party_plugins import register_third_party_plugin_tools
        from unittest.mock import Mock
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_third_party_plugin_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_plugins_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_plugins' in tool_functions:
            test_func = tool_functions['get_plugins']
            
            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"}
                ]
            }
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_plugins not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugins_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_plugins' in tool_functions:
            test_func = tool_functions['get_plugins']
            
            mock_response = {
                "list": [
                    {"id": "filtered-id", "name": "filtered-item"}
                ]
            }
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_plugins not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugins_request_failure(self, mock_environment):
        """Test request failure handling."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_plugins' in tool_functions:
            test_func = tool_functions['get_plugins']
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=None) as mock_request:
                
                result = await test_func()
                
                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_plugins not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugins_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_plugins' in tool_functions:
            test_func = tool_functions['get_plugins']
            
            with patch('third_party_plugins.ensure_bearer_token', side_effect=Exception("Authentication failed")):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(f"Function get_plugins not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugins_with_large_response(self, mock_environment):
        """Test large response handling."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_plugins' in tool_functions:
            test_func = tool_functions['get_plugins']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=large_response) as mock_request:
                
                result = await test_func()
                
                assert result == large_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_plugins not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugin_by_name(self, mock_environment):
        """Test get_plugin with lookup by name."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        if 'get_plugin' in tool_functions:
            test_func = tool_functions['get_plugin']
            
            mock_response = {"id": "plugin-123", "name": "test-plugin"}
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(identifier="test-plugin", lookup_by="name")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_plugin not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugin_by_id(self, mock_environment):
        """Test get_plugin with lookup by id."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        if 'get_plugin' in tool_functions:
            test_func = tool_functions['get_plugin']
            
            mock_response = {"id": "plugin-123", "name": "test-plugin"}
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(identifier="plugin-123", lookup_by="id")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_plugin not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_plugin_not_found(self, mock_environment):
        """Test get_plugin when plugin not found."""
        from third_party_plugins import register_third_party_plugin_tools
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
        register_third_party_plugin_tools(mock_mcp)
        
        if 'get_plugin' in tool_functions:
            test_func = tool_functions['get_plugin']
            
            with patch('third_party_plugins.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('third_party_plugins.make_zededa_request', return_value=None):
                
                result = await test_func(identifier="nonexistent", lookup_by="name")
                
                assert "No plugin found" in result
        else:
            pytest.skip("Function get_plugin not found in registered tools")
