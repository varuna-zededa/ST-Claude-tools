# zcli-kb

Lightweight command search for the ZedCloud CLI (`zcli`). Parses all zcli module
docstrings into a structured `commands.json` and exposes them as an MCP server +
Claude Code skill. No Qdrant or Ollama required.

Ask Claude: *"what zcli command creates an edge node?"* or *"what flags does network-instance create take?"*
and get back the exact syntax with required and optional flags.

## How it works

Unlike the RAG-based tools, this is a lookup tool:

1. **Parser** (`indexer/index.py`) reads `zcli/modules/*.py`, extracts the docopt
   Usage block and Commands descriptions, and writes `commands.json`
2. **MCP server** (`mcp_server/server.py`) loads `commands.json` into memory and
   does keyword scoring at query time — no embeddings, no vector DB
3. **Skill** (`skills/zcli-kb/SKILL.md`) activates automatically when you ask
   about zcli commands

## Prerequisites

| Dependency | Notes |
|------------|-------|
| Python 3.9+ | Required to create the `.venv` |
| zcli repo | Cloned locally at `~/git/zcli` (default) or any path via `--zcli-path` |

No Qdrant, no Ollama, no GPU — just Python.

## Setup

```bash
cd zcli-kb
./setup.sh                              # uses ~/git/zcli
./setup.sh --zcli-path /custom/path     # custom repo location
```

Setup creates a `.venv`, parses zcli modules into `commands.json`, installs the
skill, and registers the MCP server. Restart Claude Code after running.

## Updating the index

Re-run the indexer whenever zcli adds or changes commands:

```bash
# From the repo root:
./update-index.sh zcli-kb
./update-index.sh zcli-kb --zcli-path /custom/path
```

Or directly:
```bash
source .venv/bin/activate
python indexer/index.py --zcli-path ~/git/zcli
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `kb_info()` | Version, total command count, generated timestamp |
| `search_zcli_kb(query, command, top_k)` | Search by feature name, subcommand, or flag |

### search_zcli_kb parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | required | Feature name, action, or flag — e.g. `"create edge node"`, `"wifi config"` |
| `command` | `""` | Filter to a command group — e.g. `"edge-node"`, `"network"` |
| `top_k` | `5` | Max results to return |

## Usage in Claude Code

The `zcli-kb` skill activates automatically when your query mentions zcli or a
ZedCloud resource in a CLI context:

| Trigger | Example |
|---------|---------|
| `"zcli command for"` | "what zcli command creates a network instance?" |
| `"what flags does"` | "what flags does edge-node update take?" |
| `"how do I configure X with zcli"` | "how do I configure edgeview with zcli?" |
| `"zcli flag for"` | "what zcli flag sets the deployment tag?" |
