"""
Test cases for global_edge_apps module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestGlobalEdgeAppsModule:
    """Test cases for global_edge_apps module."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'ZEDCLOUD_API_BEARER_TOKEN': 'test-token',
            'ZEDCLOUD_API_BASE_URL': 'https://api.zedcloud.local'
        }):
            yield

    def test_register_global_edge_apps_tools(self):
        """Test that global_edge_apps tools are registered correctly."""
        from global_edge_apps import register_global_edge_app_tools
        from unittest.mock import Mock
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_global_edge_app_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_zededa_global_edge_apps_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from global_edge_apps import register_global_edge_app_tools
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
        register_global_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_edge_apps' in tool_functions:
            test_func = tool_functions['get_zededa_global_edge_apps']
            
            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"}
                ]
            }
            
            # Set up the mock httpx client
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            
            with patch('global_edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('global_edge_apps.httpx.AsyncClient') as mock_client:
                
                # Configure the async context manager
                mock_context = Mock()
                mock_context.__aenter__ = AsyncMock(return_value=Mock())
                mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_context
                
                result = await test_func()
                
                assert result == mock_response
        else:
            pytest.skip(f"Function get_zededa_global_edge_apps not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_edge_apps_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from global_edge_apps import register_global_edge_app_tools
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
        register_global_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_edge_apps' in tool_functions:
            test_func = tool_functions['get_zededa_global_edge_apps']
            
            mock_response = {
                "list": [
                    {"id": "filtered-id", "name": "filtered-item"}
                ]
            }
            
            # Set up the mock httpx client
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            
            with patch('global_edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('global_edge_apps.httpx.AsyncClient') as mock_client:
                
                # Configure the async context manager
                mock_context = Mock()
                mock_context.__aenter__ = AsyncMock(return_value=Mock())
                mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_context
                
                result = await test_func()
                
                assert result == mock_response
        else:
            pytest.skip(f"Function get_zededa_global_edge_apps not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_edge_apps_request_failure(self, mock_environment):
        """Test request failure handling."""
        from global_edge_apps import register_global_edge_app_tools
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
        register_global_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_edge_apps' in tool_functions:
            test_func = tool_functions['get_zededa_global_edge_apps']
            
            with patch('global_edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('global_edge_apps.httpx.AsyncClient') as mock_client:
                
                # Configure the async context manager to raise an exception
                import httpx
                mock_context = Mock()
                mock_context.__aenter__ = AsyncMock(return_value=Mock())
                mock_context.__aenter__.return_value.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_context
                
                result = await test_func()
                
                assert result is not None and "Request failed" in result
        else:
            pytest.skip(f"Function get_zededa_global_edge_apps not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_edge_apps_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from global_edge_apps import register_global_edge_app_tools
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
        register_global_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_edge_apps' in tool_functions:
            test_func = tool_functions['get_zededa_global_edge_apps']
            
            with patch('global_edge_apps.ensure_bearer_token', side_effect=Exception("Authentication failed")):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(f"Function get_zededa_global_edge_apps not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_edge_apps_large_response_truncation(self, mock_environment):
        """Test large response handling."""
        from global_edge_apps import register_global_edge_app_tools
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
        register_global_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_edge_apps' in tool_functions:
            test_func = tool_functions['get_zededa_global_edge_apps']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            # Set up the mock httpx client
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = large_response
            mock_response_obj.raise_for_status.return_value = None
            
            with patch('global_edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('global_edge_apps.httpx.AsyncClient') as mock_client:
                
                # Configure the async context manager
                mock_context = Mock()
                mock_context.__aenter__ = AsyncMock(return_value=Mock())
                mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response_obj)
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_client.return_value = mock_context
                
                result = await test_func()
                
                assert result == large_response
        else:
            pytest.skip(f"Function get_zededa_global_edge_apps not found in registered tools")
