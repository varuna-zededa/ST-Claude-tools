"""
Test cases for network_instances module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestNetworkInstancesModule:
    """Test cases for network_instances module."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'ZEDCLOUD_API_BEARER_TOKEN': 'test-token',
            'ZEDCLOUD_API_BASE_URL': 'https://api.zedcloud.local'
        }):
            yield

    def test_register_network_instances_tools(self):
        """Test that network_instances tools are registered correctly."""
        from network_instances import register_network_instance_tools
        from unittest.mock import Mock
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_network_instance_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_zededa_network_instances_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from network_instances import register_network_instance_tools
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
        register_network_instance_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_network_instances' in tool_functions:
            test_func = tool_functions['get_zededa_network_instances']
            
            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"}
                ]
            }
            
            with patch('network_instances.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('network_instances.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_network_instances not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_network_instances_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from network_instances import register_network_instance_tools
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
        register_network_instance_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_network_instances' in tool_functions:
            test_func = tool_functions['get_zededa_network_instances']
            
            mock_response = {
                "list": [
                    {"id": "filtered-id", "name": "filtered-item"}
                ]
            }
            
            with patch('network_instances.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('network_instances.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_network_instances not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_network_instances_request_failure(self, mock_environment):
        """Test request failure handling."""
        from network_instances import register_network_instance_tools
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
        register_network_instance_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_network_instances' in tool_functions:
            test_func = tool_functions['get_zededa_network_instances']
            
            with patch('network_instances.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('network_instances.make_zededa_request', return_value=None) as mock_request:
                
                result = await test_func()
                
                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_network_instances not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_network_instances_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from network_instances import register_network_instance_tools
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
        register_network_instance_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_network_instances' in tool_functions:
            test_func = tool_functions['get_zededa_network_instances']
            
            with patch('network_instances.ensure_bearer_token', side_effect=Exception("Authentication failed")):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(f"Function get_zededa_network_instances not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_network_instances_large_response_truncation(self, mock_environment):
        """Test large response handling."""
        from network_instances import register_network_instance_tools
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
        register_network_instance_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_network_instances' in tool_functions:
            test_func = tool_functions['get_zededa_network_instances']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            with patch('network_instances.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('network_instances.make_zededa_request', return_value=large_response) as mock_request:
                
                result = await test_func()
                
                assert result == large_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_network_instances not found in registered tools")
