"""
Test file for edge_nodes.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestEdgeNodesModule:
    """Test the edge_nodes module functions."""

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

    def test_register_edge_node_tools(self, mock_mcp):
        """Test that edge node tools are registered correctly."""
        from edge_nodes import register_edge_node_tools
        
        register_edge_node_tools(mock_mcp)
        
        # Verify that mcp.tool was called (exact count depends on implementation)
        assert mock_mcp.tool.call_count >= 3  # At least the basic CRUD operations

    @pytest.mark.asyncio
    async def test_get_zededa_nodes_success(self, mock_environment):
        """Test successful retrieval of nodes."""
        from edge_nodes import register_edge_node_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_node_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_nodes' in tool_functions:
            get_nodes_func = tool_functions['get_zededa_nodes']
            
            mock_response = {
                "list": [
                    {"id": "node1", "name": "test-node-1", "serialNumber": "SN001"},
                    {"id": "node2", "name": "test-node-2", "serialNumber": "SN002"}
                ]
            }
            
            with patch('edge_nodes.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_nodes.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_nodes_func(page_size=15, page_num=5)
                
                assert result == mock_response
                mock_request.assert_called_once()
                call_args = mock_request.call_args[0]
                assert 'api/v1/devices' in call_args[0]
                assert 'next.pageSize=15' in call_args[0]
                assert 'next.pageNum=5' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_node_by_id_success(self, mock_environment):
        """Test successful retrieval of node by ID."""
        from edge_nodes import register_edge_node_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_node_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_node_by_id' in tool_functions:
            get_node_by_id_func = tool_functions['get_zededa_node_by_id']
            
            node_id = "node-id-654"
            mock_response = {"id": node_id, "name": "test-node", "serialNumber": "SN001"}
            
            with patch('edge_nodes.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_nodes.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_node_by_id_func(node_id)
                
                assert result == mock_response
                call_args = mock_request.call_args[0]
                assert f'api/v1/devices/id/{node_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_node_by_name_success(self, mock_environment):
        """Test successful retrieval of node by name."""
        from edge_nodes import register_edge_node_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_node_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_node_by_name' in tool_functions:
            get_node_by_name_func = tool_functions['get_zededa_node_by_name']
            
            node_name = "test-node-name"
            mock_response = {"id": "654", "name": node_name, "serialNumber": "SN001"}
            
            with patch('edge_nodes.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_nodes.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_node_by_name_func(node_name)
                
                assert result == mock_response
                call_args = mock_request.call_args[0]
                assert f'api/v1/devices/name/{node_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_nodes_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from edge_nodes import register_edge_node_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_node_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_nodes' in tool_functions:
            get_nodes_func = tool_functions['get_zededa_nodes']
            
            with patch('edge_nodes.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_nodes.make_zededa_request', return_value=None):
                
                result = await get_nodes_func()
                
                assert result == "Failed to retrieve nodes."

    @pytest.mark.asyncio
    async def test_node_by_id_request_failure(self, mock_environment):
        """Test handling of request failures for node by ID."""
        from edge_nodes import register_edge_node_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_node_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_node_by_id' in tool_functions:
            get_node_by_id_func = tool_functions['get_zededa_node_by_id']
            
            node_id = "node-id-654"
            
            with patch('edge_nodes.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_nodes.make_zededa_request', return_value=None):
                
                result = await get_node_by_id_func(node_id)
                
                assert result == f"Failed to retrieve node with ID: {node_id}."


if __name__ == "__main__":
    pytest.main([__file__])
