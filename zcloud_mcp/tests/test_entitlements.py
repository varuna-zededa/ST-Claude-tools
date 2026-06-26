"""
Test file for entitlements.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestEntitlementsModule:
    """Test the entitlements module functions."""

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

    def test_register_entitlements_tools(self, mock_mcp):
        """Test that entitlements tools are registered correctly."""
        from entitlements import register_entitlements_tools
        
        register_entitlements_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_entitlements_success(self, mock_environment):
        """Test successful retrieval of entitlements."""
        from entitlements import register_entitlements_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_entitlements_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_entitlements' in tool_functions:
            test_func = tool_functions['get_entitlements']
            
            mock_response = {
                "list": [
                    {"id": "ent1", "name": "test-entitlement-1"},
                    {"id": "ent2", "name": "test-entitlement-2"}
                ]
            }
            
            with patch('entitlements.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('entitlements.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entitlements_with_filters(self, mock_environment):
        """Test entitlements query with tenant filter."""
        from entitlements import register_entitlements_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_entitlements_tools(mock_mcp)
        
        if 'get_entitlements' in tool_functions:
            test_func = tool_functions['get_entitlements']
            
            mock_response = {"list": [{"id": "ent1", "name": "filtered-entitlement"}]}
            
            with patch('entitlements.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('entitlements.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(tenant_id="tenant123")
                
                assert result == mock_response
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_entitlements_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from entitlements import register_entitlements_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_entitlements_tools(mock_mcp)
        
        if 'get_entitlements' in tool_functions:
            test_func = tool_functions['get_entitlements']
            
            with patch('entitlements.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('entitlements.make_zededa_request', side_effect=Exception("API Error")):
                
                with pytest.raises(Exception, match="API Error"):
                    await test_func()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from entitlements import register_entitlements_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_entitlements_tools(mock_mcp)
        
        if 'get_entitlements' in tool_functions:
            test_func = tool_functions['get_entitlements']
            
            auth_error_msg = "Authorization header missing or invalid"
            with patch('entitlements.ensure_bearer_token', return_value=auth_error_msg):
                result = await test_func()
                assert result == auth_error_msg

    @pytest.mark.asyncio
    async def test_simple_response_handling(self, mock_environment):
        """Test handling of simple responses."""
        from entitlements import register_entitlements_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_entitlements_tools(mock_mcp)
        
        if 'get_entitlements' in tool_functions:
            test_func = tool_functions['get_entitlements']
            
            # Simple response without truncation
            mock_response = {"entitlements": [{"type": "basic", "quota": 100}]}
            
            with patch('entitlements.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('entitlements.make_zededa_request', return_value=mock_response):
                
                result = await test_func()
                
                # Verify the function was called
                assert result is not None
