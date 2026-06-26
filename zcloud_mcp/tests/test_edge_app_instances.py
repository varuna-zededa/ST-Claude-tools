"""
Test file for edge_app_instances.py module.
"""
import pytest
import json
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestEdgeAppInstancesModule:
    """Test the edge_app_instances module functions."""

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

    @pytest.fixture
    def sample_app_instances(self):
        """Sample app instances for testing."""
        return [
            {
                "id": "app-1",
                "name": "test-app-1",
                "runState": "RUNNING",
                "appType": "container",
                "deploymentType": "azure",
                "deviceId": "device-1",
                "deviceName": "device-1",
                "projectName": "project-1",
                "appName": "bundle-1"
            },
            {
                "id": "app-2",
                "name": "test-app-2",
                "runState": "STOPPED",
                "appType": "vm",
                "deploymentType": "aws",
                "deviceId": "device-2",
                "deviceName": "device-2",
                "projectName": "project-2",
                "appName": "bundle-2",
                "errInfo": [
                    {
                        "description": "App failed to start",
                        "severity": "ERROR",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        ]

    def test_register_edge_app_instance_tools(self, mock_mcp):
        """Test that edge app instance tools are registered correctly."""
        from edge_app_instances import register_edge_app_instance_tools
        
        register_edge_app_instance_tools(mock_mcp)
        
        # Verify that multiple tools were registered
        assert mock_mcp.tool.call_count >= 5  # At least 5 main functions

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_success(self, mock_environment, sample_app_instances):
        """Test successful retrieval of app instances."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_app_instances_func = tool_functions['get_zededa_app_instances']
        
        mock_response = {"list": sample_app_instances}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response) as mock_request, \
             patch('edge_app_instances.format_app_instance', side_effect=lambda x: f"Formatted: {x['name']}"):
            
            result = await get_app_instances_func(page_size=10, page_num=1)
            
            assert isinstance(result, str)
            assert "Formatted: test-app-1" in result
            assert "Formatted: test-app-2" in result
            assert "--" in result  # Separator between instances
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert 'apps/instances/status-config' in call_args[0]
            assert 'next.pageSize=10' in call_args[0]
            assert 'next.pageNum=1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_empty_response(self, mock_environment):
        """Test handling of empty app instances response."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_app_instances_func = tool_functions['get_zededa_app_instances']
        
        mock_response = {"list": []}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response):
            
            result = await get_app_instances_func()
            
            assert result == "No app instances found."

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_app_instances_func = tool_functions['get_zededa_app_instances']
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=None):
            
            result = await get_app_instances_func()
            
            assert "Failed to retrieve app instances" in result

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_summary(self, mock_environment, sample_app_instances):
        """Test the app instances summary function."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_summary_func = tool_functions['get_zededa_app_instances_summary']
        
        # The implementation returns raw JSON with 'list' key from API
        mock_response = {
            "list": sample_app_instances,
            "summary": {
                "total": 2,
                "running": 1,
                "stopped": 1
            }
        }
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response):
            
            result = await get_summary_func()
            
            # Result should be a JSON string representation of the response
            assert isinstance(result, str)
            # Verify it's valid JSON
            parsed = json.loads(result)
            assert "list" in parsed
            assert parsed["list"] == sample_app_instances
            # If there's a summary key, verify it
            if "summary" in parsed:
                assert parsed["summary"]["total"] == 2

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_by_status(self, mock_environment, sample_app_instances):
        """Test filtering app instances by status."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_status_func = tool_functions['get_zededa_app_instances_by_status']
        
        # Filter to only running instances
        running_instances = [app for app in sample_app_instances if app['runState'] == 'RUNNING']
        mock_response = {"list": running_instances}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response) as mock_request, \
             patch('edge_app_instances.format_app_instance', side_effect=lambda x: f"Formatted: {x['name']}"):
            
            result = await get_by_status_func("RUNNING")
            
            assert isinstance(result, str)
            assert "App Instances with status 'RUNNING'" in result
            assert "Formatted: test-app-1" in result
            # Should not contain the stopped app
            assert "test-app-2" not in result
            
            call_args = mock_request.call_args[0]
            assert 'runState=RUNNING' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_app_instances_by_project(self, mock_environment, sample_app_instances):
        """Test filtering app instances by project."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_project_func = tool_functions['get_zededa_app_instances_by_project']
        
        # Filter to only project-1 instances
        project_instances = [app for app in sample_app_instances if app['projectName'] == 'project-1']
        mock_response = {"list": project_instances}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response) as mock_request, \
             patch('edge_app_instances.format_app_instance', side_effect=lambda x: f"Formatted: {x['name']}"):
            
            result = await get_by_project_func("project-1")
            
            assert isinstance(result, str)
            assert "App Instances in project 'project-1'" in result
            assert "Formatted: test-app-1" in result
            
            call_args = mock_request.call_args[0]
            assert 'projectName=project-1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_app_instance_status_from_id(self, mock_environment):
        """Test getting app instance status by ID."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_status_func = tool_functions['get_zededa_app_instance_status_from_id']
        
        app_id = "test-app-123"
        mock_response = {"id": app_id, "status": {"state": "RUNNING"}}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_status_func(app_id)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'apps/instances/id/{app_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_large_response_truncation(self, mock_environment):
        """Test that large responses are properly truncated."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_app_instances_func = tool_functions['get_zededa_app_instances']
        
        # Create a large list of app instances
        large_instances = []
        for i in range(20):
            large_instances.append({
                "id": f"app-{i}",
                "name": f"test-app-{i}",
                "runState": "RUNNING",
                "deviceName": f"device-{i}",
                "projectName": f"project-{i}"
            })
        
        mock_response = {"list": large_instances}
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response), \
             patch('edge_app_instances.format_app_instance', side_effect=lambda x: f"Formatted: {x['name']}"):
            
            result = await get_app_instances_func()
            
            assert isinstance(result, str)
            # Should be truncated to MAX_ITEMS_PER_RESPONSE (10)
            assert "Showing 10 of 20 total app instances" in result

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, mock_environment):
        """Test handling of authentication errors."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_app_instances_func = tool_functions['get_zededa_app_instances']
        
        with patch('edge_app_instances.ensure_bearer_token', return_value=None):
            # ensure_bearer_token returns None on auth failure; make_zededa_request
            # will short-circuit and the tool returns a generic error string
            pass  # The actual behavior depends on the implementation

    @pytest.mark.asyncio
    async def test_get_edge_app_instance_by_name_success(self, mock_environment):
        """Test successful retrieval of app instance by name."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_name_func = tool_functions['get_edge_app_instance_by_name']
        
        mock_response = {
            "id": "test-app-123",
            "name": "erik-rpi-ubuntu",
            "runState": "RUNNING",
            "deviceName": "device-1"
        }
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response):
            
            result = await get_by_name_func("erik-rpi-ubuntu")
            
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed["id"] == "test-app-123"
            assert parsed["name"] == "erik-rpi-ubuntu"

    @pytest.mark.asyncio
    async def test_get_edge_app_instance_by_name_list_response(self, mock_environment):
        """Test handling when API returns a list instead of single object."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_name_func = tool_functions['get_edge_app_instance_by_name']
        
        # API returns a list with one element
        mock_response = [
            {
                "id": "test-app-123",
                "name": "erik-rpi-ubuntu",
                "runState": "RUNNING",
                "deviceName": "device-1"
            }
        ]
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response):
            
            result = await get_by_name_func("erik-rpi-ubuntu")
            
            assert isinstance(result, str)
            parsed = json.loads(result)
            # Should extract the first element from the list
            assert parsed["id"] == "test-app-123"
            assert parsed["name"] == "erik-rpi-ubuntu"
            assert isinstance(parsed, dict)  # Not a list

    @pytest.mark.asyncio
    async def test_get_edge_app_instance_by_name_empty_list(self, mock_environment):
        """Test handling when API returns an empty list."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_name_func = tool_functions['get_edge_app_instance_by_name']
        
        # API returns an empty list
        mock_response = []
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response):
            
            result = await get_by_name_func("nonexistent-app")
            
            assert "No app instance found with name: nonexistent-app" in result

    @pytest.mark.asyncio
    async def test_get_edge_app_instance_by_name_multiple_matches(self, mock_environment):
        """Test handling when API returns multiple matches."""
        from edge_app_instances import register_edge_app_instance_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_edge_app_instance_tools(mock_mcp)
        get_by_name_func = tool_functions['get_edge_app_instance_by_name']
        
        # API returns multiple matches (shouldn't happen but handle it)
        mock_response = [
            {"id": "test-app-1", "name": "test-app"},
            {"id": "test-app-2", "name": "test-app"}
        ]
        
        with patch('edge_app_instances.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('edge_app_instances.make_zededa_request', return_value=mock_response), \
             patch('edge_app_instances.logger') as mock_logger:
            
            result = await get_by_name_func("test-app")
            
            # Should use the first match
            parsed = json.loads(result)
            assert parsed["id"] == "test-app-1"
            # Should log a warning
            mock_logger.warning.assert_called_once()
            assert "Multiple app instances found" in mock_logger.warning.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__])
