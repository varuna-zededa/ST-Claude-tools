"""
Test file for projects.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any

# We need to import the functions to test them
# Since projects.py uses register pattern, we'll test the module directly


class TestProjectsModule:
    """Test the projects module functions."""

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

    def test_register_project_tools(self, mock_mcp):
        """Test that project tools are registered correctly."""
        from projects import register_project_tools
        
        register_project_tools(mock_mcp)
        
        # Verify that mcp.tool was called for each function (9 tools now)
        # get_projects, get_project, get_project_status_config_summary, query_project_status,
        # query_project_status_config, get_project_tags, get_project_status, get_project_events, get_project_metrics
        assert mock_mcp.tool.call_count == 9

    @pytest.mark.asyncio
    async def test_get_projects_success(self, mock_environment):
        """Test successful retrieval of projects."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        
        # Register the tools
        register_project_tools(mock_mcp)
        
        # Get the function
        get_projects_func = tool_functions['get_projects']
        
        mock_response = {
            "list": [
                {"id": "1", "name": "test-project-1"},
                {"id": "2", "name": "test-project-2"}
            ]
        }
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_projects_func(page_size=20, page_num=1)
            
            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert 'api/v1/projects' in call_args[0]
            assert 'next.pageSize=20' in call_args[0]
            assert 'next.pageNum=1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_projects_with_defaults(self, mock_environment):
        """Test projects retrieval with default parameters."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_projects_func = tool_functions['get_projects']
        
        mock_response = {"list": []}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_projects_func()
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert 'next.pageSize=20' in call_args[0]
            assert 'next.pageNum=1' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_projects_with_large_response(self, mock_environment):
        """Test projects retrieval with response limiting."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_projects_func = tool_functions['get_projects']
        
        # Create a response with more items than the limit
        large_list = [{"id": str(i), "name": f"project-{i}"} for i in range(20)]
        mock_response = {"list": large_list}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response):
            
            result = await get_projects_func()
            
            # Should be limited and have truncation info
            assert isinstance(result, dict)
            assert "list" in result
            assert len(result["list"]) <= 10  # MAX_ITEMS_PER_RESPONSE
            if len(large_list) > 10:
                assert "_truncated" in result

    @pytest.mark.asyncio
    async def test_get_project_by_id_success(self, mock_environment):
        """Test successful retrieval of project by ID."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_project_func = tool_functions['get_project']
        
        project_id = "12345678-1234-1234-1234-123456789abc"
        mock_response = {"id": project_id, "name": "test-project"}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_project_func(project_id, lookup_by="id")
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/projects/id/{project_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_project_by_name_success(self, mock_environment):
        """Test successful retrieval of project by name."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_project_func = tool_functions['get_project']
        
        project_name = "test-project"
        mock_response = {"id": "123", "name": project_name}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_project_func(project_name, lookup_by="name")
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/projects/name/{project_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_projects_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_projects_func = tool_functions['get_projects']
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=None):
            
            result = await get_projects_func()
            
            assert result == "Failed to retrieve projects."

    @pytest.mark.asyncio
    async def test_project_by_id_request_failure(self, mock_environment):
        """Test handling of request failures for project by ID."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_project_func = tool_functions['get_project']
        
        project_id = "12345678-1234-1234-1234-123456789abc"
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=None):
            
            result = await get_project_func(project_id, lookup_by="id")
            
            assert "Project not found" in result

    @pytest.mark.asyncio
    async def test_get_project_status_config_summary_success(self, mock_environment):
        """Test successful retrieval of project status config summary."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_summary_func = tool_functions['get_project_status_config_summary']
        
        mock_response = {"summary": {"total": 10, "active": 8}}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_summary_func(create_plot=False)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert 'api/v1/projects/status-config' in call_args[0]
            assert 'summary=true' in call_args[0]

    @pytest.mark.asyncio
    async def test_query_project_status_success(self, mock_environment):
        """Test successful query of project status."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        query_func = tool_functions['query_project_status']
        
        mock_response = {"list": [{"id": "1", "status": "ACTIVE"}]}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await query_func(name_pattern="test*", page_size=10)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert 'api/v1/projects/status' in call_args[0]
            assert 'namePattern=test*' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_project_events_success(self, mock_environment):
        """Test successful retrieval of project events."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_events_func = tool_functions['get_project_events']
        
        project_id = "12345678-1234-1234-1234-123456789abc"
        mock_response = {"list": [{"event": "created", "timestamp": "2024-01-01"}]}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_events_func(project_id, lookup_by="id", severity="INFO")
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/projects/id/{project_id}/events' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_project_metrics_success(self, mock_environment):
        """Test successful retrieval of project metrics."""
        from projects import register_project_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_project_tools(mock_mcp)
        get_metrics_func = tool_functions['get_project_metrics']
        
        project_name = "test-project"
        mock_response = {"data": [{"timestamp": "2024-01-01", "value": 100}]}
        
        with patch('projects.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('projects.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_metrics_func(project_name, "CPU_USAGE", lookup_by="name", create_plot=False)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/projects/name/{project_name}/timeSeries/CPU_USAGE' in call_args[0]


if __name__ == "__main__":
    pytest.main([__file__])
