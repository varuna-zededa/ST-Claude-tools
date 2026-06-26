"""
Test file for networks.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestNetworksModule:
    """Test the networks module functions."""

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

    def test_register_network_tools(self, mock_mcp):
        """Test that network tools are registered correctly."""
        from networks import register_network_tools
        
        register_network_tools(mock_mcp)
        
        # Verify that mcp.tool was called for each function
        assert mock_mcp.tool.call_count == 3  # get_zededa_networks, get_zededa_network_by_id, get_zededa_network_by_name

    @pytest.mark.asyncio
    async def test_get_zededa_networks_success(self, mock_environment):
        """Test successful retrieval of networks."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_networks_func = tool_functions['get_zededa_networks']
        
        mock_response = {
            "list": [
                {"id": "net1", "name": "test-network-1", "type": "local"},
                {"id": "net2", "name": "test-network-2", "type": "cloud"}
            ]
        }
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_networks_func(page_size=30, page_num=2)
            
            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert 'api/v1/networks' in call_args[0]
            assert 'next.pageSize=30' in call_args[0]
            assert 'next.pageNum=2' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_networks_with_defaults(self, mock_environment):
        """Test networks retrieval with default parameters."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_networks_func = tool_functions['get_zededa_networks']
        
        mock_response = {"list": []}
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_networks_func()
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert 'next.pageSize=20' in call_args[0]
            assert 'next.pageNum=1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_network_by_id_success(self, mock_environment):
        """Test successful retrieval of network by ID."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_network_by_id_func = tool_functions['get_zededa_network_by_id']
        
        network_id = "network-id-987"
        mock_response = {"id": network_id, "name": "test-network", "type": "local"}
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_network_by_id_func(network_id)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/networks/id/{network_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_network_by_name_success(self, mock_environment):
        """Test successful retrieval of network by name."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_network_by_name_func = tool_functions['get_zededa_network_by_name']
        
        network_name = "test-network"
        mock_response = {"id": "987", "name": network_name, "type": "cloud"}
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_network_by_name_func(network_name)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/networks/name/{network_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_networks_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_networks_func = tool_functions['get_zededa_networks']
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=None):
            
            result = await get_networks_func()
            
            assert result == "Failed to retrieve networks."

    @pytest.mark.asyncio
    async def test_network_by_id_request_failure(self, mock_environment):
        """Test handling of request failures for network by ID."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_network_by_id_func = tool_functions['get_zededa_network_by_id']
        
        network_id = "network-id-987"
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=None):
            
            result = await get_network_by_id_func(network_id)
            
            assert result == f"Failed to retrieve network with ID: {network_id}."

    @pytest.mark.asyncio
    async def test_network_by_name_request_failure(self, mock_environment):
        """Test handling of request failures for network by name."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_network_by_name_func = tool_functions['get_zededa_network_by_name']
        
        network_name = "test-network"
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=None):
            
            result = await get_network_by_name_func(network_name)
            
            assert result == f"Failed to retrieve network with name: {network_name}."

    @pytest.mark.asyncio
    async def test_networks_with_large_response(self, mock_environment):
        """Test networks retrieval with response limiting."""
        from networks import register_network_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_network_tools(mock_mcp)
        get_networks_func = tool_functions['get_zededa_networks']
        
        # Create a response with more items than the limit
        large_list = [{"id": str(i), "name": f"network-{i}"} for i in range(20)]
        mock_response = {"list": large_list}
        
        with patch('networks.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('networks.make_zededa_request', return_value=mock_response):
            
            result = await get_networks_func()
            
            # Should be limited and have truncation info
            assert isinstance(result, dict)
            assert "list" in result
            assert len(result["list"]) <= 10  # MAX_ITEMS_PER_RESPONSE
            if len(large_list) > 10:
                assert "_truncated" in result


if __name__ == "__main__":
    pytest.main([__file__])
