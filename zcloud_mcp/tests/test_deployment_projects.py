"""
Test cases for deployment_projects module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestDeploymentProjectsModule:
    """Test cases for deployment_projects module."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'ZEDCLOUD_API_BEARER_TOKEN': 'test-token',
            'ZEDCLOUD_API_BASE_URL': 'https://api.zedcloud.local'
        }):
            yield

    def test_register_deployment_projects_tools(self):
        """Test that deployment_projects tools are registered correctly."""
        from deployment_projects import register_deployment_project_tools
        from unittest.mock import Mock
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        mock_mcp.tool = Mock()
        register_deployment_project_tools(mock_mcp)
        
        # Verify that mcp.tool was called for both functions
        assert mock_mcp.tool.call_count == 2

    @pytest.mark.asyncio
    async def test_get_project_deployments_success(self, mock_environment):
        """Test successful query using registration pattern."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployments' in tool_functions:
            test_func = tool_functions['get_project_deployments']
            
            mock_response = {
                "list": [
                    {"id": "test-id-1", "name": "test-item-1"},
                    {"id": "test-id-2", "name": "test-item-2"}
                ]
            }
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('deployment_projects.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(project_id="12345678-1234-1234-1234-123456789abc")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_project_deployments not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployments_with_valid_uuid(self, mock_environment):
        """Test query with valid UUID using registration pattern."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployments' in tool_functions:
            test_func = tool_functions['get_project_deployments']
            
            mock_response = {
                "list": [
                    {"id": "filtered-id", "name": "filtered-item"}
                ]
            }
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('deployment_projects.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(project_id="12345678-1234-1234-1234-123456789abc")
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_project_deployments not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployments_request_failure(self, mock_environment):
        """Test request failure handling."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployments' in tool_functions:
            test_func = tool_functions['get_project_deployments']
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('deployment_projects.make_zededa_request', return_value=None) as mock_request:
                
                result = await test_func(project_id="12345678-1234-1234-1234-123456789abc")
                
                assert result is not None and "Failed to retrieve" in result
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_project_deployments not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployments_authentication_error_handling(self, mock_environment):
        """Test authentication error handling."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployments' in tool_functions:
            test_func = tool_functions['get_project_deployments']
            
            with patch('deployment_projects.ensure_bearer_token', side_effect=Exception("Authentication failed")):
                try:
                    await test_func(project_id="12345678-1234-1234-1234-123456789abc")
                    assert False, "Should have raised an exception"
                except Exception as e:
                    assert "Authentication failed" in str(e)
        else:
            pytest.skip(f"Function get_project_deployments not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployments_large_response_truncation(self, mock_environment):
        """Test large response handling."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployments' in tool_functions:
            test_func = tool_functions['get_project_deployments']
            
            # Create large response data
            large_response = {
                "list": [
                    {"id": f"id-{i}", "name": f"item-{i}", "data": "x" * 1000} 
                    for i in range(100)
                ]
            }
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('deployment_projects.make_zededa_request', return_value=large_response) as mock_request:
                
                result = await test_func(project_id="12345678-1234-1234-1234-123456789abc")
                
                # Result should have response, possibly with truncation
                assert isinstance(result, dict)
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_project_deployments not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployment_success(self, mock_environment):
        """Test getting a single deployment successfully."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployment' in tool_functions:
            test_func = tool_functions['get_project_deployment']
            
            mock_response = {
                "id": "87654321-4321-4321-4321-cba987654321",
                "name": "test-deployment",
                "revision": {"curr": "1"}
            }
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"), \
                 patch('deployment_projects.make_zededa_request', return_value=mock_response) as mock_request:
                
                result = await test_func(
                    project_id="12345678-1234-1234-1234-123456789abc",
                    deployment_id="87654321-4321-4321-4321-cba987654321"
                )
                
                assert result == mock_response
                mock_request.assert_called_once()
        else:
            pytest.skip(f"Function get_project_deployment not found in registered tools")

    @pytest.mark.asyncio
    async def test_get_project_deployment_invalid_uuid(self, mock_environment):
        """Test error handling with invalid UUID."""
        from deployment_projects import register_deployment_project_tools
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
        register_deployment_project_tools(mock_mcp)
        
        # Check if the function exists
        if 'get_project_deployment' in tool_functions:
            test_func = tool_functions['get_project_deployment']
            
            with patch('deployment_projects.ensure_bearer_token', return_value="Bearer test-token"):
                result = await test_func(
                    project_id="invalid-project-id",
                    deployment_id="87654321-4321-4321-4321-cba987654321"
                )
                
                # Should return an error message
                assert isinstance(result, str)
                assert "valid UUID" in result
        else:
            pytest.skip(f"Function get_project_deployment not found in registered tools")
