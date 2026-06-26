---
name: zcloud_swagger_mcp
description: >
  Search indexed Swagger/OpenAPI documentation for ZedCloud API endpoints.
  Use when the user asks about available API endpoints, request/response schemas,
  or needs to find the right API call for a given operation. Trigger when the user
  asks "what API", "which endpoint", "how do I call", "find the endpoint for",
  or references a ZedCloud service operation.
---

# Swagger API Docs Skill

You have three MCP tools available:
- `search_api_docs` — semantic vector search over all indexed endpoints
- `get_endpoint` — exact lookup by HTTP method + path
- `list_api_sources` — list all indexed service names

## MCP availability check — do this first

Before answering, check whether `search_api_docs` is available as a tool in this session.

**If `search_api_docs` IS available:** use it. Do not answer from general knowledge.

**If `search_api_docs` is NOT available:** start your response with this block:

> ⚠️ **Unverified answer** — the zcloud_swagger_mcp MCP server is not running in this session.
> Restart Claude Code to activate it, then re-ask.

## Workflow

### Finding an endpoint
1. Call `search_api_docs` with a natural language query describing the operation.
2. If results are thin, refine with a service name filter using the `source` parameter.
3. If you already know the exact method + path, use `get_endpoint` directly.

### Listing what's indexed
Call `list_api_sources` to see all available services before searching.

## Response format

**Endpoint:** `METHOD /path`
**Service:** `source_name`
**Summary:** ...

**Request:**
```json
{ ...request body schema... }
```

**Response:**
```json
{ ...response schema... }
```

**Source:** from `search_api_docs` result payload
