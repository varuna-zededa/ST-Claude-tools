# Mock Data Files

> **Source:** Taken from [zededa/zededa-ai-agents](https://github.com/zededa/zededa-ai-agents)
> (`mcp/mocks/`) with minor tweaks for the Claude Code MCP environment.

This directory contains mock JSON files used when the MCP server runs in `USE_MOCK_API_MCP_DATA=true` mode.

## Purpose

Mock data allows you to:
- Test the agent without connecting to a real Zededa server
- Run tests in CI/CD pipelines
- Develop offline
- Create predictable test scenarios

## Implementation

Mock data loading is centralized in `mcp/utils.py` via the `load_mock_json()` function. All MCP tools and the authentication module import and use this function to load mock data consistently.

## File Naming Convention

### List Tools
Files for listing multiple objects:
- `<object-type>-list.json`
- Example: `brands-list.json`, `projects-list.json`, `edge-nodes-list.json`

### Get by ID Tools
Files for fetching a specific object by ID:
- `<object-type>-<id>.json`
- Example: `brands-brand-001.json`, `projects-project-123.json`

### Get by Name Tools
Files for fetching a specific object by name:
- `<object-type>-<name>.json`
- Example: `brands-SuperMicro.json`, `projects-Production.json`
- Note: Slashes in names are replaced with underscores

### Special Files
Files for special operations:
- `user-self.json` - Mock user data for authentication/get_user_info()
- `edge-nodes-summary.json` - Mock summary data for edge node status and distribution

## Example Files

This directory includes example mock files:
- `brands-list.json` - List of hardware brands
- `brands-SuperMicro.json` - Single brand detail
- `projects-list.json` - List of projects
- `user-self.json` - Mock user data for authentication
- `edge-nodes-summary.json` - Edge node status summary with distribution data

## Creating Your Own Mock Files

1. Determine which tool you want to mock
2. Use the appropriate naming pattern
3. Create a JSON file with the expected response structure
4. Place it in this directory

### Example: Mock a project by ID

Filename: `projects-my-project-id.json`

```json
{
  "id": "my-project-id",
  "name": "My Test Project",
  "description": "A test project for development",
  "title": "Test",
  "type": "TAG_TYPE_PROJECT"
}
```

## Response Format

Mock files should match the actual API response format, including:
- Response wrapper objects (e.g., `{"list": [...]}` for list endpoints)
- Pagination metadata (e.g., `next.pageNum`, `next.pageSize`)
- All required fields for the object type

## Usage

1. Enable mock mode: `export USE_MOCK_API_MCP_DATA=true`
2. Start the server: `python mcp/mcpserver.py`
3. The server will automatically load mock files from this directory when available
4. If a mock file is not found, it falls back to the real API

## Tips

- Use realistic data that matches your test scenarios
- Include edge cases (empty lists, error conditions, etc.)
- Keep files organized by object type
- Version control your mock files for reproducible tests
