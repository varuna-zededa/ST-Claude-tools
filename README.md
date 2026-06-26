# ST-Claude-tools

A collection of MCP server tools and RAG pipelines for Claude Code, used by the Systems Test team.

## Tools

| Folder | Description |
|--------|-------------|
| [zcloud-swagger-rag](./zcloud-swagger-rag/) | Semantic search over ZedCloud Swagger/OpenAPI docs |
| [eve-kb-rag](./eve-kb-rag/) | EVE OS knowledge base — docs, pillar agent source, and edgeview |

## Setup

Run the top-level `setup.sh` with the tool name to set up a specific tool:

```bash
./setup.sh zcloud-swagger-rag
./setup.sh eve-kb-rag
```

Each tool creates its own `.venv`, writes a local `config.json`, installs its Claude Code skill, and registers its MCP server in `~/.mcp.json`.

Restart Claude Code after running setup to activate the new MCP server and skill.
