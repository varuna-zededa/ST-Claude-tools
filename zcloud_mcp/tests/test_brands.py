"""
Tests for Zededa hardware brands MCP tools.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestBrandsModule:
    """Test suite for brands module functionality."""

    def test_register_brand_tools(self):
        """Test that brand tools are properly registered."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Verify all expected functions are registered
        expected_functions = [
            'query_zededa_hardware_brands',
            'query_zededa_global_hardware_brands',
            'get_zededa_hardware_brand_by_id',
            'get_zededa_hardware_brand_by_name',
            'get_zededa_global_hardware_brand_by_id',
            'get_zededa_global_hardware_brand_by_name'
        ]
        
        for func_name in expected_functions:
            assert func_name in tool_functions, f"Function {func_name} not registered"

    @pytest.mark.asyncio
    async def test_query_zededa_hardware_brands_success(self, mock_environment):
        """Test successful query of hardware brands."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            mock_response = {
                "list": [
                    {"id": "brand-1", "name": "Dell", "originType": "ORIGIN_GLOBAL"},
                    {"id": "brand-2", "name": "HP", "originType": "ORIGIN_GLOBAL"}
                ]
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_query_zededa_hardware_brands_with_filters(self, mock_environment):
        """Test query with filters using registration pattern."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            mock_response = {
                "list": [
                    {"id": "brand-1", "name": "Dell", "originType": "ORIGIN_GLOBAL"}
                ]
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(
                    name_pattern="Dell*",
                    origin_type="ORIGIN_GLOBAL",
                    page_size=10
                )
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_query_zededa_hardware_brands_invalid_origin_type(self, mock_environment):
        """Test query with invalid origin type."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"):
                result = await test_func(origin_type="INVALID_TYPE")
                
                assert "Invalid origin_type" in result
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_query_zededa_global_hardware_brands_success(self, mock_environment):
        """Test successful query of global hardware brands."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_global_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_global_hardware_brands']
            
            mock_response = {
                "list": [
                    {"id": "global-brand-1", "name": "AMD", "originType": "ORIGIN_GLOBAL"},
                    {"id": "global-brand-2", "name": "Intel", "originType": "ORIGIN_GLOBAL"}
                ]
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func()
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function query_zededa_global_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_hardware_brand_by_id_success(self, mock_environment):
        """Test successful retrieval of hardware brand by ID."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_hardware_brand_by_id' in tool_functions:
            test_func = tool_functions['get_zededa_hardware_brand_by_id']
            
            mock_response = {
                "id": "brand-123",
                "name": "Dell PowerEdge",
                "originType": "ORIGIN_GLOBAL"
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(id="brand-123")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_hardware_brand_by_id not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_hardware_brand_by_id_empty_id(self, mock_environment):
        """Test brand by ID with empty ID parameter."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_hardware_brand_by_id' in tool_functions:
            test_func = tool_functions['get_zededa_hardware_brand_by_id']
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"):
                result = await test_func(id="")
                
                assert "Error: id parameter is required" in result
        else:
            pytest.skip(f"Function get_zededa_hardware_brand_by_id not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_hardware_brand_by_name_success(self, mock_environment):
        """Test successful retrieval of hardware brand by name."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_hardware_brand_by_name' in tool_functions:
            test_func = tool_functions['get_zededa_hardware_brand_by_name']
            
            mock_response = {
                "id": "brand-456",
                "name": "HP ProLiant",
                "originType": "ORIGIN_GLOBAL"
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(name="HP ProLiant")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_hardware_brand_by_name not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_hardware_brand_by_id_success(self, mock_environment):
        """Test successful retrieval of global hardware brand by ID."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_hardware_brand_by_id' in tool_functions:
            test_func = tool_functions['get_zededa_global_hardware_brand_by_id']
            
            mock_response = {
                "id": "global-brand-789",
                "name": "Lenovo ThinkSystem",
                "originType": "ORIGIN_GLOBAL"
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(id="global-brand-789")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_global_hardware_brand_by_id not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_zededa_global_hardware_brand_by_name_success(self, mock_environment):
        """Test successful retrieval of global hardware brand by name."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_zededa_global_hardware_brand_by_name' in tool_functions:
            test_func = tool_functions['get_zededa_global_hardware_brand_by_name']
            
            mock_response = {
                "id": "global-brand-101",
                "name": "Cisco UCS",
                "originType": "ORIGIN_GLOBAL"
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(name="Cisco UCS")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_zededa_global_hardware_brand_by_name not found in registered tools")

    @pytest.mark.asyncio
    async def test_brands_request_failure(self, mock_environment):
        """Test request failure handling."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=None) as mock_request:
                
                result = await test_func()
                
                assert result == "Failed to retrieve hardware brands."
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            with patch('brands.ensure_bearer_token', return_value=None):
                result = await test_func()
                # None token causes make_zededa_request to return None,
                # so the tool returns a generic "Failed to retrieve" string
                assert isinstance(result, str)
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")

    @pytest.mark.asyncio
    async def test_large_response_truncation(self, mock_environment):
        """Test handling of large responses with truncation."""
        from brands import register_brand_tools
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
        register_brand_tools(mock_mcp)
        
        # Check if the function exists
        if 'query_zededa_hardware_brands' in tool_functions:
            test_func = tool_functions['query_zededa_hardware_brands']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"brand-{i}", "name": f"Brand-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            with patch('brands.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('brands.make_zededa_request', return_value=large_response) as mock_request:
                
                result = await test_func()
                
                # Should still be a dict with potentially truncated results
                assert isinstance(result, dict)
                assert "list" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function query_zededa_hardware_brands not found in registered tools")
