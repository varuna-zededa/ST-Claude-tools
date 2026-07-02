# ST-Claude-tools

A collection of MCP server tools and RAG pipelines for Claude Code, used by the Systems Test team.

## Tools

| Folder | Description |
|--------|-------------|
| [zedcloud-kb-rag](./zedcloud-kb-rag/) | ZedCloud knowledge base — docs, Swagger endpoints, proto definitions, and Go service source |
| [eve-kb-rag](./eve-kb-rag/) | EVE OS knowledge base — docs, pillar agent source, and edgeview |
| [skills/st-testplan-generator](./skills/st-testplan-generator/) | Claude Code skill for generating ZedCloud API and EVE device test plans |

---

## Prerequisites

Install these before running any `setup.sh`.

### Required for all tools

| Dependency | Version | How to install |
|------------|---------|----------------|
| Python 3 | ≥ 3.9 | `brew install python` or system package manager |
| Qdrant | any | `docker run -p 6333:6333 qdrant/qdrant` |
| Ollama | any | [ollama.com/download](https://ollama.com/download) |
| `nomic-embed-text` model | any | `ollama pull nomic-embed-text` |
| Claude Code CLI | any | [claude.ai/code](https://claude.ai/code) |

Qdrant must be running at `http://localhost:6333` when you run `setup.sh`. Ollama must be running and have `nomic-embed-text` available — setup will pull it automatically if Ollama is running but the model is not yet downloaded.

### Per-tool requirements

#### `zedcloud-kb-rag`

| Requirement | Detail |
|-------------|--------|
| ZedCloud repo | Cloned locally at `~/git/zedcloud` (default) or any path passed via `--zcloud-path` |
| GitHub token *(optional)* | Set `GITHUB_TOKEN` to index directly from GitHub without a local clone |
| Python packages | `qdrant-client`, `ollama`, `fastmcp`, `requests`, `fastembed`, `PyYAML` — installed automatically into `.venv` by setup |

#### `eve-kb-rag`

| Requirement | Detail |
|-------------|--------|
| EVE repo | Cloned locally at `~/git/eve` (default) or any path passed via `--eve-path` |
| Python packages | `qdrant-client`, `ollama`, `fastmcp`, `requests`, `fastembed` — installed automatically into `.venv` by setup |

#### `skills/st-testplan-generator`

No setup script needed. Copy `SKILL.md` to `~/.claude/skills/st-testplan-generator/SKILL.md` to install. Requires `zcloud-kb` and `eve-kb` MCP servers to be running for full functionality.

---

## Setup

Run the top-level `setup.sh` with the tool name:

```bash
./setup.sh zedcloud-kb-rag                                    # uses ~/git/zedcloud
./setup.sh zedcloud-kb-rag --zcloud-path /custom/path        # custom repo location

./setup.sh eve-kb-rag                                         # uses ~/git/eve
./setup.sh eve-kb-rag --eve-path /custom/path/eve            # custom repo location
```

Each tool creates its own `.venv`, writes a local `config.json`, installs its Claude Code skill, and registers its MCP server in `~/.mcp.json`.

After setup, run the indexer for the tool (see the tool's own README for indexer options), then restart Claude Code to activate the new MCP server and skill.
