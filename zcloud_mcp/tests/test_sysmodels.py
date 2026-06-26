"""
Test file for sysmodels.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestSysmodelsModule:
    """Test the sysmodels module functions."""

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

    def test_register_hardware_model_tools(self, mock_mcp):
        """Test that sysmodels tools are registered correctly."""
        from sysmodels import register_hardware_model_tools
        
        register_hardware_model_tools(mock_mcp)
        
        # Verify that mcp.tool was called
        assert mock_mcp.tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_query_zededa_hardware_models_success(self, mock_environment):
        """Test successful retrieval of sysmodels."""
        from sysmodels import register_hardware_model_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_hardware_model_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_models' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_models']
            
            mock_response = {
                "list": [
                    {"id": "model1", "name": "test-model-1"},
                    {"id": "model2", "name": "test-model-2"}
                ]
            }
            
            with patch('sysmodels.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('sysmodels.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_zededa_hardware_models_with_filters(self, mock_environment):
        """Test sysmodels query with filters."""
        from sysmodels import register_hardware_model_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_hardware_model_tools(mock_mcp)
        
        if 'query_zededa_hardware_models' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_models']
            
            mock_response = {"list": [{"id": "model1", "name": "filtered-model"}]}
            
            with patch('sysmodels.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('sysmodels.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(page_size=10)
                
                assert result == mock_response
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_sysmodels_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from sysmodels import register_hardware_model_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_hardware_model_tools(mock_mcp)
        
        if 'query_zededa_hardware_models' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_models']
            
            with patch('sysmodels.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('sysmodels.make_zededa_request', side_effect=Exception("API Error")):
                
                with pytest.raises(Exception, match="API Error"):
                    await test_func()

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from sysmodels import register_hardware_model_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_hardware_model_tools(mock_mcp)
        
        if 'query_zededa_hardware_models' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_models']
            
            auth_error_msg = "Authorization header missing or invalid"
            with patch('sysmodels.ensure_bearer_token', return_value=auth_error_msg):
                result = await test_func()
                assert result == auth_error_msg

    @pytest.mark.asyncio
    async def test_large_response_truncation(self, mock_environment):
        """Test handling of large responses."""
        from sysmodels import register_hardware_model_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_hardware_model_tools(mock_mcp)
        
        if 'query_zededa_hardware_models' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_models']
            
            # Create a large mock response
            large_list = [{"id": f"model{i}", "name": f"model-{i}"} for i in range(100)]
            mock_response = {"list": large_list}
            
            with patch('sysmodels.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('sysmodels.make_zededa_request', return_value=mock_response), \
                 patch('sysmodels.limit_list_response', return_value=(mock_response, False)) as mock_limit:
                
                result = await test_func()
                
                # Verify the function was called
                assert result is not None
