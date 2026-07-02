# ST-Claude-tools

Claude Code guidance for this repo. Read this before making changes.

## What this repo is

A collection of Claude Code tools for the Systems Test team at Zededa. It contains two kinds of things:

1. **RAG knowledge base tools** — index source repos into Qdrant and expose them as MCP servers + Claude Code skills. Currently: `zedcloud-kb-rag` and `eve-kb-rag`.
2. **Live API MCP server** — `zcloud_mcp` talks directly to the ZedCloud API and exposes it as MCP tools. Not a RAG pipeline.
3. **Shared skills** — `skills/` contains Claude Code skills that don't belong to a single tool, e.g. `st-testplan-generator`.

## Audience

All tools in this repo are built for **test engineers**, not developers. Users need to understand system behavior, find API endpoints, write test cases, and verify device-side behavior.

When working in this repo, frame responses around:
- "how to verify", "what API to call", "expected behavior", "test this by..."
- Swagger/API docs, service behavior, and proto definitions — not Go internals or implementation detail
- For EVE: CLI verification commands and collect-info tarball handoff to dev — not pillar internals or pubsub debugging
- Source code results are secondary — useful for understanding what the API validates, not for coding against

## Repo structure

```
setup.sh                    # dispatcher — runs any tool's setup.sh, then installs skills/
update-index.sh             # dispatcher — activates tool venv and runs indexer/index.py
skills/                     # shared Claude Code skills (auto-installed by setup.sh)
  st-testplan-generator/
    SKILL.md
zedcloud-kb-rag/            # ZedCloud knowledge base RAG tool
  indexer/index.py          # indexes docs, swagger, protos, Go source into Qdrant
  mcp_server/server.py      # MCP server exposing search_zcloud_kb, read_zcloud_file, kb_info
  skills/zcloud-kb/SKILL.md # skill installed to ~/.claude/skills/zcloud-kb/
  setup.sh                  # creates venv, checks Qdrant/Ollama, registers MCP, installs skill
  requirements.txt
eve-kb-rag/                 # EVE OS knowledge base RAG tool (same structure as zedcloud-kb-rag)
  indexer/index.py
  mcp_server/server.py
  skills/eve-kb/SKILL.md
  setup.sh
  requirements.txt
zcloud_mcp/                 # Live ZedCloud API MCP server (not a RAG tool)
  mcpserver.py              # MCP server entry point
  *.py                      # one file per ZedCloud resource type
  swagger/                  # bundled swagger specs
  tests/                    # pytest suite with mock fixtures
  setup.sh                  # separate setup — does not follow the RAG tool pattern
```

## Top-level scripts

### setup.sh

Dispatches to a tool's own `setup.sh`, then auto-installs all skills from `skills/`.

```bash
./setup.sh zedcloud-kb-rag                  # full tool setup + skills
./setup.sh zedcloud-kb-rag --no-skills      # full tool setup, skip skills/ installation
./setup.sh eve-kb-rag --eve-path /custom    # custom repo path
./setup.sh skills                           # install skills only, no tool setup
```

Skills from `skills/` are always installed after a tool setup unless `--no-skills` is passed.
Each tool's own `setup.sh` also installs its own skill (from `<tool>/skills/`).

### update-index.sh

Activates a tool's venv and runs its indexer. Run this to refresh the KB after source changes.

```bash
./update-index.sh zedcloud-kb-rag
./update-index.sh zedcloud-kb-rag --source github --branch main --reset
./update-index.sh zedcloud-kb-rag --skip-source   # faster; skips Go source, indexes specs only
./update-index.sh eve-kb-rag --source github --branch eve-9.13
```

Requires the tool's venv to exist (i.e. `setup.sh` must have been run first).

## RAG tool conventions

Each RAG tool (`zedcloud-kb-rag`, `eve-kb-rag`) follows the same internal structure:

- `setup.sh` — creates `.venv`, checks Qdrant at `localhost:6333` and Ollama, writes `config.json`, installs skill, registers MCP in `~/.mcp.json`
- `requirements.txt` — Python deps (qdrant-client, ollama, fastmcp, requests, fastembed)
- `indexer/index.py` — standalone script; activated via `update-index.sh` or directly
- `mcp_server/server.py` — stdio MCP server; spawned by Claude Code on demand
- `skills/<skill-name>/SKILL.md` — installed to `~/.claude/skills/<skill-name>/`
- `config.json` — written by setup, read by mcp_server; not committed (gitignored)

Both tools use **hybrid search** (dense embeddings via `nomic-embed-text` + BM25 sparse) fused with RRF. All chunks carry a `version` field (git branch) for provenance filtering.

## Skills

### Tool-owned skills
Each RAG tool ships its own skill under `<tool>/skills/`. These are installed by the tool's own `setup.sh`.

### Shared skills
`skills/` at the repo root contains skills not tied to a single tool. These are installed automatically by the root `setup.sh` after any tool setup, or via `./setup.sh skills`.

To update an installed skill after editing its `SKILL.md`:
```bash
cp skills/st-testplan-generator/SKILL.md ~/.claude/skills/st-testplan-generator/SKILL.md
```
Or re-run `./setup.sh skills`.

### st-testplan-generator skill dependencies
`skills/st-testplan-generator/SKILL.md` depends on both `zcloud-kb` and `eve-kb` MCP tools.
The skill checks for their availability at runtime and falls back to user-provided documents
if either is missing.

## Adding a new RAG tool

1. Create `<tool-name>/` following the structure above
2. Add `indexer/index.py`, `mcp_server/server.py`, `skills/<skill>/SKILL.md`, `requirements.txt`, `setup.sh`
3. The root `setup.sh` and `update-index.sh` pick up the new tool automatically — no changes needed

## Adding a new shared skill

1. Create `skills/<skill-name>/SKILL.md`
2. The root `setup.sh` picks it up automatically — no changes needed
3. Copy to `~/.claude/skills/<skill-name>/SKILL.md` to activate in the current session

## zcloud_mcp

`zcloud_mcp/` is a separate live API MCP server — not a RAG tool. It has its own `setup.sh`,
`pyproject.toml`, pytest suite under `tests/`, and Dockerfile. Do not apply RAG tool patterns
to it. Refer to `zcloud_mcp/README.md` for its own setup and usage instructions.

## What not to commit

- `.venv/` directories
- `config.json` files (written by setup, contain local paths)
- `__pycache__/` and `*.pyc`
- `.env` files
