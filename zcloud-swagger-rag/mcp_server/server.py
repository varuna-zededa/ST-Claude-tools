#!/usr/bin/env python3
"""MCP server exposing Swagger/OpenAPI docs from Qdrant to Claude Code.

Tools:
  - search_api_docs  : semantic vector search over all indexed endpoints
  - get_endpoint     : exact lookup by HTTP method + path
  - list_api_sources : list all indexed service names
"""

import asyncio
import json
from pathlib import Path

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

# ---------------------------------------------------------------------------
# Config — written by setup.sh
# ---------------------------------------------------------------------------

_CONFIG_FILE = Path(__file__).parent.parent / "config.json"


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}


_CFG = _load_config()
OLLAMA_URL  = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL  = _CFG.get("qdrant_url", "http://localhost:6333")
COLLECTION  = "swagger_docs"

qdrant = QdrantClient(url=QDRANT_URL)
server = Server("swagger-docs")


def embed(text: str) -> list[float]:
    resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]


def format_result(payload: dict, score: float = None) -> str:
    lines = []
    if score is not None:
        lines.append(f"[score={score:.3f}] {payload['method']} {payload['path']}  ({payload['source']})")
    else:
        lines.append(f"{payload['method']} {payload['path']}  ({payload['source']})")

    if payload.get("summary"):
        lines.append(f"Summary: {payload['summary']}")
    if payload.get("tags"):
        lines.append(f"Tags: {', '.join(payload['tags'])}")

    full_op = payload.get("full_operation", "")
    if full_op:
        try:
            parsed = json.loads(full_op)
            lines.append("\nFull spec:")
            lines.append(json.dumps(parsed, indent=2))
        except Exception:
            lines.append(f"\nFull spec:\n{full_op}")

    return "\n".join(lines)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_api_docs",
            description=(
                "Semantic search over Swagger/OpenAPI documentation. "
                "Use to find API endpoints by feature, purpose, or description. "
                "Returns matching endpoints with their full specs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query, e.g. 'create a new user' or 'list all network interfaces'",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results to return (default 5, max 20)",
                    },
                    "source": {
                        "type": "string",
                        "description": "Filter by service name, e.g. 'zedge_user_service' (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_endpoint",
            description=(
                "Retrieve the full spec for a specific API endpoint by HTTP method and path. "
                "Use when you know the exact endpoint you need."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, PATCH, DELETE",
                    },
                    "path": {
                        "type": "string",
                        "description": "Endpoint path, e.g. /v1/users/{id}",
                    },
                    "source": {
                        "type": "string",
                        "description": "Service name to narrow the lookup (optional)",
                    },
                },
                "required": ["method", "path"],
            },
        ),
        Tool(
            name="list_api_sources",
            description="List all indexed API service names available for querying.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_api_docs":
        query  = arguments["query"]
        limit  = min(int(arguments.get("limit", 5)), 20)
        source = arguments.get("source")

        vector      = embed(query)
        filter_cond = None
        if source:
            filter_cond = Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            )

        results = qdrant.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=limit,
            query_filter=filter_cond,
            with_payload=True,
        ).points

        if not results:
            return [TextContent(type="text", text="No matching endpoints found.")]

        sections = [format_result(r.payload, r.score) for r in results]
        return [TextContent(type="text", text="\n\n---\n\n".join(sections))]

    elif name == "get_endpoint":
        method = arguments["method"].upper()
        path   = arguments["path"]
        source = arguments.get("source")

        must = [
            FieldCondition(key="method", match=MatchValue(value=method)),
            FieldCondition(key="path",   match=MatchValue(value=path)),
        ]
        if source:
            must.append(FieldCondition(key="source", match=MatchValue(value=source)))

        results, _ = qdrant.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=must),
            limit=5,
            with_payload=True,
        )

        if not results:
            return [TextContent(type="text", text=f"Endpoint {method} {path} not found in index.")]

        sections = [format_result(r.payload) for r in results]
        return [TextContent(type="text", text="\n\n---\n\n".join(sections))]

    elif name == "list_api_sources":
        sources = {}
        offset  = None
        while True:
            batch, offset = qdrant.scroll(
                collection_name=COLLECTION,
                limit=200,
                offset=offset,
                with_payload=["source", "api_title"],
            )
            for pt in batch:
                src   = pt.payload.get("source", "unknown")
                title = pt.payload.get("api_title", src)
                sources[src] = title
            if offset is None:
                break

        if not sources:
            return [TextContent(type="text", text="No API sources indexed yet. Run indexer/index.py first.")]

        lines = ["Indexed API services:\n"]
        for src, title in sorted(sources.items()):
            lines.append(f"  {src}  ({title})")
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
