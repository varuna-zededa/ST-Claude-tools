"""
Test file for edge_apps.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestEdgeAppsModule:
    """Test the edge_apps module functions."""

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

    def test_register_edge_app_tools(self, mock_mcp):
        """Test that edge app tools are registered correctly."""
        from edge_apps import register_edge_app_tools
        
        register_edge_app_tools(mock_mcp)
        
        # Verify that mcp.tool was called (exact count depends on implementation)
        assert mock_mcp.tool.call_count >= 3  # At least the basic CRUD operations

    @pytest.mark.asyncio
    async def test_get_zededa_edge_apps_success(self, mock_environment):
        """Test successful retrieval of edge apps."""
        from edge_apps import register_edge_app_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_edge_apps' in tool_functions:
            get_edge_apps_func = tool_functions['get_zededa_edge_apps']
            
            mock_response = {
                "list": [
                    {"id": "app1", "name": "test-app-1", "version": "1.0"},
                    {"id": "app2", "name": "test-app-2", "version": "2.0"}
                ]
            }
            
            with patch('edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_apps.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_edge_apps_func(page_size=75, page_num=2)
                
                assert result == mock_response
                mock_request.assert_called_once()
                call_args = mock_request.call_args[0]
                assert 'api/v1/apps' in call_args[0]
                # Page size is capped at 50 in the implementation
                assert 'next.pageSize=50' in call_args[0]
                assert 'next.pageNum=2' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_edge_app_by_id_success(self, mock_environment):
        """Test successful retrieval of edge app by ID."""
        from edge_apps import register_edge_app_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_edge_app_by_id' in tool_functions:
            get_edge_app_by_id_func = tool_functions['get_zededa_edge_app_by_id']
            
            app_id = "edge-app-id-321"
            mock_response = {"id": app_id, "name": "test-edge-app", "version": "1.0"}
            
            with patch('edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_apps.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_edge_app_by_id_func(app_id)
                
                assert result == mock_response
                call_args = mock_request.call_args[0]
                assert f'api/v1/apps/id/{app_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_edge_app_by_name_success(self, mock_environment):
        """Test successful retrieval of edge app by name."""
        from edge_apps import register_edge_app_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_edge_app_by_name' in tool_functions:
            get_edge_app_by_name_func = tool_functions['get_zededa_edge_app_by_name']
            
            app_name = "test-edge-app-name"
            mock_response = {"id": "321", "name": app_name, "version": "1.0"}
            
            with patch('edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_apps.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await get_edge_app_by_name_func(app_name)
                
                assert result == mock_response
                call_args = mock_request.call_args[0]
                assert f'api/v1/apps/name/{app_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_edge_apps_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from edge_apps import register_edge_app_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_edge_apps' in tool_functions:
            get_edge_apps_func = tool_functions['get_zededa_edge_apps']
            
            with patch('edge_apps.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('edge_apps.make_zededa_request', return_value=None):
                
                result = await get_edge_apps_func()
                
                assert result == "Failed to retrieve edge applications."


if __name__ == "__main__":
    pytest.main([__file__])
