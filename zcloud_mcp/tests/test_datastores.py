"""
Test file for datastores.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestDatastoresModule:
    """Test the datastores module functions."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server for testing."""
        mcp = Mock()
        mcp.tool = Mock()
        return mcp

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {'ZEDCLOUD_BASE_URL': 'https://api.test.com'}):
            yield

    def test_register_datastore_tools(self, mock_mcp):
        """Test that datastore tools are registered correctly."""
        from datastores import register_datastore_tools
        
        register_datastore_tools(mock_mcp)
        
        # Verify that mcp.tool was called for each function
        assert mock_mcp.tool.call_count == 4  # get_zededa_datastores, get_zededa_datastore_by_id, get_zededa_datastore_by_name, get_zededa_datastores_by_project

    @pytest.mark.asyncio
    async def test_get_zededa_datastores_success(self, mock_environment):
        """Test successful retrieval of datastores."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastores_func = tool_functions['get_zededa_datastores']
        
        mock_response = {
            "list": [
                {"id": "ds1", "name": "test-datastore-1"},
                {"id": "ds2", "name": "test-datastore-2"}
            ]
        }
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_datastores_func(page_size=25, page_num=2)
            
            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert 'api/v1/datastores' in call_args[0]
            assert 'next.pageSize=25' in call_args[0]
            assert 'next.pageNum=2' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_datastores_with_defaults(self, mock_environment):
        """Test datastores retrieval with default parameters."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastores_func = tool_functions['get_zededa_datastores']
        
        mock_response = {"list": []}
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_datastores_func()
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert 'next.pageSize=20' in call_args[0]
            assert 'next.pageNum=1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_datastore_by_id_success(self, mock_environment):
        """Test successful retrieval of datastore by ID."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastore_by_id_func = tool_functions['get_zededa_datastore_by_id']
        
        datastore_id = "test-datastore-456"
        mock_response = {"id": datastore_id, "name": "test-datastore"}
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_datastore_by_id_func(datastore_id)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/datastores/id/{datastore_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_datastore_by_name_success(self, mock_environment):
        """Test successful retrieval of datastore by name."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastore_by_name_func = tool_functions['get_zededa_datastore_by_name']
        
        datastore_name = "test-datastore"
        mock_response = {"id": "456", "name": datastore_name}
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_datastore_by_name_func(datastore_name)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/datastores/name/{datastore_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_datastores_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastores_func = tool_functions['get_zededa_datastores']
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=None):
            
            result = await get_datastores_func()
            
            assert result == "Failed to retrieve datastores."

    @pytest.mark.asyncio
    async def test_datastore_by_id_request_failure(self, mock_environment):
        """Test handling of request failures for datastore by ID."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastore_by_id_func = tool_functions['get_zededa_datastore_by_id']
        
        datastore_id = "test-datastore-456"
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=None):
            
            result = await get_datastore_by_id_func(datastore_id)
            
            assert result == f"Failed to retrieve datastore with ID: {datastore_id}."

    @pytest.mark.asyncio
    async def test_datastore_by_name_request_failure(self, mock_environment):
        """Test handling of request failures for datastore by name."""
        from datastores import register_datastore_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_datastore_tools(mock_mcp)
        get_datastore_by_name_func = tool_functions['get_zededa_datastore_by_name']
        
        datastore_name = "test-datastore"
        
        with patch('datastores.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('datastores.make_zededa_request', return_value=None):
            
            result = await get_datastore_by_name_func(datastore_name)
            
            assert result == f"Failed to retrieve datastore with name: {datastore_name}."


if __name__ == "__main__":
    pytest.main([__file__])
