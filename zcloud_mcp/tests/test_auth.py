"""
Test file for auth.py module.
"""
import pytest
from unittest.mock import patch, Mock

from auth import ensure_bearer_token


class TestEnsureBearerToken:
    """Test the ensure_bearer_token function."""

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self):
        """Test with a valid Bearer token."""
        with patch('auth.get_http_headers') as mock_headers:
            mock_headers.return_value = {
                "x-zedcloud-authorization": "Bearer valid-token-123"
            }
            
            result = await ensure_bearer_token()
            assert result == "Bearer valid-token-123"

    @pytest.mark.asyncio
    async def test_invalid_token_format(self):
        """Test with invalid token format."""
        with patch('auth.get_http_headers') as mock_headers:
            mock_headers.return_value = {
                "x-zedcloud-authorization": "Invalid token-123"
            }
            
            result = await ensure_bearer_token()
            assert result is None

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test with missing authorization header."""
        with patch('auth.get_http_headers') as mock_headers:
            mock_headers.return_value = {}
            
            result = await ensure_bearer_token()
            assert result is None

    @pytest.mark.asyncio
    async def test_bearer_token_case_sensitive(self):
        """Test that Bearer token check is case-sensitive."""
        with patch('auth.get_http_headers') as mock_headers:
            mock_headers.return_value = {
                "x-zedcloud-authorization": "bearer valid-token-123"  # lowercase
            }
            
            result = await ensure_bearer_token()
            assert result is None

    @pytest.mark.asyncio
    async def test_empty_authorization_header(self):
        """Test with empty authorization header."""
        with patch('auth.get_http_headers') as mock_headers:
            mock_headers.return_value = {
                "x-zedcloud-authorization": ""
            }
            
            result = await ensure_bearer_token()
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
