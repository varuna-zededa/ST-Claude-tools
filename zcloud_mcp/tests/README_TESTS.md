# Unit Tests for Zededa MCP Server

> **Source:** Taken from [zededa/zededa-ai-agents](https://github.com/zededa/zededa-ai-agents)
> (`mcp/tests/`) with minor tweaks for the Claude Code MCP environment.

This directory contains comprehensive unit tests for the Zededa MCP (Model Context Protocol) server implementation.

## Test Files Overview

### 1. `test_zededa.py` - Utility Function Tests (31 tests)
Tests the core utility functions used throughout the MCP server.

### 2. `test_mcp_tools.py` - MCP Tool Function Tests (29 tests)  
Tests all 22 MCP tool functions with comprehensive parameter coverage by calling them directly via the `.fn` attribute.

**Total Test Coverage: 60 tests, 100% passing, ~2 seconds execution time**

## Test Coverage

The test suite covers the following components:

### Core Functions
- **`format_app_instance`**: Tests formatting of application instance data with various scenarios including error information
- **`convert_time_to_seconds`**: Tests time conversion from ISO 8601 and Unix timestamp formats
- **`make_zededa_request`**: Tests HTTP request handling with proper error handling and timeout scenarios
- **`ensure_bearer_token`**: Tests Bearer token validation and authorization header handling

### API Logic Testing
- **URL Construction**: Tests proper URL building for various API endpoints
- **Query Parameter Handling**: Tests encoding and formatting of query parameters
- **Response Processing**: Tests handling of API response data and error scenarios
- **JSON Serialization**: Tests handling of response serialization and error cases

### Error Handling
- **Edge Cases**: Tests handling of null values, empty data structures, and malformed input
- **Network Errors**: Tests handling of HTTP errors, connection failures, and timeouts
- **Data Validation**: Tests proper validation of input parameters and response data

## Test Structure

The tests are organized into the following classes:

1. **TestFormatAppInstance**: Tests app instance data formatting
2. **TestConvertTimeToSeconds**: Tests time conversion functionality
3. **TestMakeZededaRequest**: Tests HTTP request handling
4. **TestEnsureBearerToken**: Tests authentication token validation
5. **TestAPILogic**: Tests API endpoint logic and URL construction
6. **TestErrorHandling**: Tests edge cases and error scenarios

### MCP Tools Tests (`test_mcp_tools.py`)

7. **TestMCPTools**: Tests all 22 FastMCP-decorated tool functions with complete parameter coverage:
   - **Projects**: get_zededa_projects, get_zededa_project_by_id, get_zededa_project_by_name
   - **Datastores**: get_zededa_datastores, get_zededa_datastore_by_id, get_zededa_datastore_by_name  
   - **Images**: get_zededa_images, get_zededa_image_by_id, get_zededa_image_by_name
   - **Edge Apps**: get_zededa_edge_apps, get_zededa_edge_app_by_id, get_zededa_edge_app_by_name
   - **Nodes**: get_zededa_nodes, get_zededa_node_by_id, get_zededa_node_by_name
   - **Networks**: get_zededa_networks, get_zededa_network_by_id, get_zededa_network_by_name
   - **App Instances**: get_zededa_app_instances, get_zededa_app_instance_status_from_id
   - **Logs & Events**: get_zededa_app_instance_logs_by_id, get_zededa_app_instance_events_by_id
   - **Error scenarios**: Authentication failures, network errors, empty responses
   - **Parameter testing**: All optional parameters, default values, and edge cases

## Running Tests

### Prerequisites

Install the test dependencies:

```bash
pip install -e ".[test]"
```

### Running All Tests

```bash
# Run both utility function tests and MCP tool tests (60 tests total)
pytest test_zededa.py test_mcp_tools.py -v

# Quick summary without verbose output
pytest test_zededa.py test_mcp_tools.py --tb=short
```

### Running Individual Test Suites

```bash
# Run only utility function tests (31 tests)
pytest test_zededa.py -v

# Run only MCP tool tests (29 tests)  
pytest test_mcp_tools.py -v
```

### Running Specific Test Classes

```bash
# Test only formatting functions
pytest test_zededa.py::TestFormatAppInstance -v

# Test only HTTP request handling
pytest test_zededa.py::TestMakeZededaRequest -v

# Test only time conversion
pytest test_zededa.py::TestConvertTimeToSeconds -v
```

### Running with Coverage

```bash
pytest test_zededa.py --cov=zededa --cov-report=html
```

## Test Features

### Mocking Strategy
- Uses `unittest.mock` to mock external dependencies (httpx, environment variables)
- Mocks FastMCP framework components for isolated testing
- Provides realistic mock responses for API scenarios

### Async Testing
- Uses `pytest-asyncio` for testing asynchronous functions
- Properly handles async context managers and coroutines
- Tests timeout scenarios and concurrent request handling

### Edge Case Coverage
- Tests with null/None inputs
- Tests with empty data structures
- Tests with malformed JSON responses
- Tests with network failures and HTTP errors

### Data Validation
- Tests proper handling of missing fields in API responses
- Tests URL encoding for special characters
- Tests proper error message formatting

## Test Data

The tests use realistic mock data that mirrors the actual Zededa API responses:

- **App Instances**: Complete app instance objects with device information, status, and error details
- **API Responses**: Properly structured responses with lists, pagination, and metadata
- **Time Formats**: Various ISO 8601 and Unix timestamp formats
- **Error Scenarios**: Realistic error responses and network failures

## Continuous Integration

These tests are designed to be run in CI/CD pipelines and provide:

- Fast execution (all tests complete in under 3 seconds)
- Deterministic results with proper mocking
- Clear error messages for debugging failures
- Coverage reporting for code quality metrics

## Bug Fixes

The test suite helped identify and fix several bugs in the original code:

1. **Null Safety**: Fixed handling of None values in error information
2. **Empty Lists**: Fixed IndexError when error info list is empty
3. **String Parsing**: Improved time string parsing with proper whitespace handling
4. **Error Handling**: Enhanced error information extraction with null checks

## Future Enhancements

Potential areas for expanding the test coverage:

1. **Integration Tests**: Tests with real MCP server interactions
2. **Performance Tests**: Load testing for concurrent requests
3. **Security Tests**: Tests for authentication and authorization edge cases
4. **End-to-End Tests**: Complete workflow testing with mock Zededa API

## Dependencies

- `pytest>=7.0.0`: Test framework
- `pytest-asyncio>=0.21.0`: Async test support
- `pytest-mock>=3.10.0`: Enhanced mocking capabilities
- `httpx`: HTTP client (mocked in tests)
- `fastmcp`: MCP framework (partially mocked)
