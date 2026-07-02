# ST-Claude-tools

A collection of MCP server tools and RAG pipelines for Claude Code, used by the Systems Test team.

## Tools

| Folder | Description | README |
|--------|-------------|--------|
| [zedcloud-kb-rag](./zedcloud-kb-rag/) | ZedCloud knowledge base — docs, Swagger endpoints, proto definitions, and Go service source | [README](./zedcloud-kb-rag/README.md) |
| [eve-kb-rag](./eve-kb-rag/) | EVE OS knowledge base — docs, pillar agent source, and edgeview | [README](./eve-kb-rag/README.md) |
| [skills/st-testplan-generator](./skills/st-testplan-generator/) | Claude Code skill for generating ZedCloud API and EVE device test plans | [SKILL.md](./skills/st-testplan-generator/SKILL.md) |

---

## Prerequisites

Install these before running any `setup.sh`.

### Required for all tools

| Dependency | Install guide | Notes |
|------------|--------------|-------|
| Python 3.9+ | [python.org/downloads](https://www.python.org/downloads/) | Required to create each tool's `.venv` |
| Qdrant | [qdrant.tech/documentation/guides/installation](https://qdrant.tech/documentation/guides/installation/) | Must be running at `localhost:6333` before setup |
| Docker *(recommended for Qdrant)* | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) | Easiest way to run Qdrant: `docker run -p 6333:6333 qdrant/qdrant` |
| Ollama | [ollama.com/download](https://ollama.com/download) | Must be running; setup pulls `nomic-embed-text` automatically |
| Claude Code | [claude.ai/code](https://claude.ai/code) | Required to use MCP servers and skills |

Qdrant must be running at `http://localhost:6333` when you run `setup.sh`. Ollama must be running — setup pulls `nomic-embed-text` automatically if the model is not yet downloaded.

### Per-tool requirements

#### `zedcloud-kb-rag`

| Requirement | Detail |
|-------------|--------|
| ZedCloud repo | Cloned locally at `~/git/zedcloud` (default) or any path passed via `--zcloud-path` |
| GitHub token *(optional)* | Set `GITHUB_TOKEN` to index directly from GitHub without a local clone |

#### `eve-kb-rag`

| Requirement | Detail |
|-------------|--------|
| EVE repo | Cloned locally at `~/git/eve` (default) or any path passed via `--eve-path` |

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

Each tool creates its own `.venv`, writes a local `config.json`, installs its Claude Code skill,
registers its MCP server in `~/.mcp.json`, and **automatically installs all skills from `skills/`**.

### Install skills only

To install or update the Claude Code skills without running a full tool setup (no Qdrant or
Ollama required):

```bash
./setup.sh skills
```

This copies all skills from `skills/` to `~/.claude/skills/` and is safe to re-run anytime
to pick up skill updates from the repo.

### Skip skills installation

To run a tool setup without installing skills:

```bash
./setup.sh zedcloud-kb-rag --no-skills
./setup.sh eve-kb-rag --no-skills
```

After any setup, restart Claude Code to activate the new MCP servers and skills.

### Updating the index

After the source repo changes, refresh the knowledge base index using `update-index.sh`:

```bash
./update-index.sh zedcloud-kb-rag                                        # local clone
./update-index.sh zedcloud-kb-rag --source github --branch main
./update-index.sh zedcloud-kb-rag --reset                                # wipe and rebuild
./update-index.sh zedcloud-kb-rag --skip-source                          # API specs only (faster)

./update-index.sh eve-kb-rag                                             # local clone
./update-index.sh eve-kb-rag --source github --branch eve-9.13 --reset
```

Run `./update-index.sh` with no arguments to see all available options per tool.
