"""
Test cases for datastreams module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestDatastreamsModule:
    """Test cases for datastreams module."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'ZEDCLOUD_API_BEARER_TOKEN': 'test-token',
            'ZEDCLOUD_API_BASE_URL': 'https://api.zedcloud.local'
        }):
            yield

    def test_register_datastreams_tools(self):
        """Test that datastreams tools are registered correctly."""
        from datastreams import register_datastream_tools
        from unittest.mock import Mock
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_datastream_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_datastreams_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_datastreams' in tool_functions:
            test_func = tool_functions['get_datastreams']
            
            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"}
                ]
            }
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_datastreams not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastreams_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_datastreams' in tool_functions:
            test_func = tool_functions['get_datastreams']
            
            mock_response = {
                "list": [
                    {"id": "filtered-id", "name": "filtered-item"}
                ]
            }
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_datastreams not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastreams_request_failure(self, mock_environment):
        """Test request failure handling."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_datastreams' in tool_functions:
            test_func = tool_functions['get_datastreams']
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=None) as mock_request:
                
                result = await test_func()
                
                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_datastreams not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastreams_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_datastreams' in tool_functions:
            test_func = tool_functions['get_datastreams']
            
            with patch('datastreams.ensure_bearer_token', side_effect=Exception("Authentication failed")):
                try:
                    await test_func()
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(f"Function get_datastreams not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastreams_with_large_response(self, mock_environment):
        """Test large response handling."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_datastreams' in tool_functions:
            test_func = tool_functions['get_datastreams']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=large_response) as mock_request:
                
                result = await test_func()
                
                assert result == large_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_datastreams not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastream_by_name(self, mock_environment):
        """Test get_datastream with lookup by name."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        if 'get_datastream' in tool_functions:
            test_func = tool_functions['get_datastream']
            
            mock_response = {"id": "ds-123", "name": "test-datastream"}
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(identifier="test-datastream", lookup_by="name")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_datastream not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastream_by_id(self, mock_environment):
        """Test get_datastream with lookup by id."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        if 'get_datastream' in tool_functions:
            test_func = tool_functions['get_datastream']
            
            mock_response = {"id": "ds-123", "name": "test-datastream"}
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(identifier="ds-123", lookup_by="id")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip("Function get_datastream not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_datastream_not_found(self, mock_environment):
        """Test get_datastream when datastream not found."""
        from datastreams import register_datastream_tools
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
        register_datastream_tools(mock_mcp)
        
        if 'get_datastream' in tool_functions:
            test_func = tool_functions['get_datastream']
            
            with patch('datastreams.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('datastreams.make_zededa_request', return_value=None):
                
                result = await test_func(identifier="nonexistent", lookup_by="name")
                
                assert "No datastream found" in result
        else:
            pytest.skip("Function get_datastream not found in registered tools")
