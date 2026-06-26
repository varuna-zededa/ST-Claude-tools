"""
Test file for images.py module.
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any


class TestImagesModule:
    """Test the images module functions."""

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

    def test_register_image_tools(self, mock_mcp):
        """Test that image tools are registered correctly."""
        from images import register_image_tools
        
        register_image_tools(mock_mcp)
        
        # Verify that mcp.tool was called for each function
        assert mock_mcp.tool.call_count == 9  # Multiple image-related tools including eve-images, baseos images, etc.

    @pytest.mark.asyncio
    async def test_get_zededa_images_success(self, mock_environment):
        """Test successful retrieval of images."""
        from images import register_image_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_image_tools(mock_mcp)
        get_images_func = tool_functions['get_zededa_images']
        
        mock_response = {
            "list": [
                {"id": "img1", "name": "test-image-1", "architecture": "amd64"},
                {"id": "img2", "name": "test-image-2", "architecture": "arm64"}
            ]
        }
        
        with patch('images.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('images.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_images_func(page_size=20, page_num=4)
            
            assert result == mock_response
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert 'api/v1/apps/images' in call_args[0]
            assert 'next.pageSize=20' in call_args[0]
            assert 'next.pageNum=4' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_image_by_id_success(self, mock_environment):
        """Test successful retrieval of image by ID."""
        from images import register_image_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_image_tools(mock_mcp)
        get_image_by_id_func = tool_functions['get_zededa_image_by_id']
        
        image_id = "image-id-789"
        mock_response = {"id": image_id, "name": "test-image", "architecture": "amd64"}
        
        with patch('images.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('images.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_image_by_id_func(image_id)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/apps/images/id/{image_id}' in call_args[0]

    @pytest.mark.asyncio
    async def test_get_zededa_image_by_name_success(self, mock_environment):
        """Test successful retrieval of image by name."""
        from images import register_image_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_image_tools(mock_mcp)
        get_image_by_name_func = tool_functions['get_zededa_image_by_name']
        
        image_name = "test-image-name"
        mock_response = {"id": "789", "name": image_name, "architecture": "arm64"}
        
        with patch('images.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('images.make_zededa_request', return_value=mock_response) as mock_request:
            
            result = await get_image_by_name_func(image_name)
            
            assert result == mock_response
            call_args = mock_request.call_args[0]
            assert f'api/v1/apps/images/name/{image_name}' in call_args[0]

    @pytest.mark.asyncio
    async def test_images_request_failure(self, mock_environment):
        """Test handling of request failures."""
        from images import register_image_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_image_tools(mock_mcp)
        get_images_func = tool_functions['get_zededa_images']
        
        with patch('images.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('images.make_zededa_request', return_value=None):
            
            result = await get_images_func()
            
            assert result == "Failed to retrieve images."

    @pytest.mark.asyncio
    async def test_image_by_id_request_failure(self, mock_environment):
        """Test handling of request failures for image by ID."""
        from images import register_image_tools
        
        mock_mcp = Mock()
        mock_mcp.USE_MOCK_API_MCP_DATA = False
        tool_functions = {}
        
        def mock_tool(tags=None):
            def decorator(func):
                tool_functions[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        register_image_tools(mock_mcp)
        get_image_by_id_func = tool_functions['get_zededa_image_by_id']
        
        image_id = "image-id-789"
        
        with patch('images.ensure_bearer_token', return_value="Bearer test-token"), \
             patch('images.make_zededa_request', return_value=None):
            
            result = await get_image_by_id_func(image_id)
            
            assert result == f"Failed to retrieve image with ID: {image_id}."


if __name__ == "__main__":
    pytest.main([__file__])
