"""
Pytest configuration for MCP module tests.
"""
import pytest
import sys
import os
from pathlib import Path

# Add the project root and mcp directories to Python path so modules can be imported
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcp"))

@pytest.fixture(scope="session")
def mock_environment():
    """Mock environment variables for all tests."""
    test_env = {
        'ZEDCLOUD_BASE_URL': 'https://api.test.com',
        'ZEDCLOUD_TOKEN': 'test-token'
    }
    
    # Store original environment
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)
    
    # Set test environment
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture
def mock_response_success():
    """Standard successful response fixture."""
    return {"status": "success", "data": []}

@pytest.fixture
def mock_response_list():
    """Standard list response fixture."""
    return {
        "list": [
            {"id": "1", "name": "item-1"},
            {"id": "2", "name": "item-2"}
        ],
        "next": {}
    }

# Configure asyncio for async tests (moved to top-level conftest.py)

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
