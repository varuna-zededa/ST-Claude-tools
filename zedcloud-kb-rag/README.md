# zedcloud-kb-rag

Local RAG knowledge base for the ZedCloud microservices codebase. Indexes documentation,
Swagger API specs, proto definitions, and service source code into Qdrant for semantic
search via Claude Code.

## What gets indexed

Four parts, all using hybrid search (dense + BM25):

| doc_type       | Source                                        | Content                              |
|----------------|-----------------------------------------------|--------------------------------------|
| `zcloud_docs`  | `docs/**/*.md`                                | Design docs, architecture, features  |
| `service_docs` | `srvs/*/README.md`                            | Per-service overviews                |
| `library_docs` | `libs/*/README.md`                            | Shared library documentation         |
| `swagger_docs` | `libs/zmsg/zapiservices/swagger/*.swagger.json`, `srvs/*/api/swagger.yaml`, etc. | One chunk per API endpoint; operation stored unresolved (`$ref` names like `#/definitions/AppInstance` point to the data model) |
| `proto_defs`   | `**/*.proto` (excl. vendor)                   | Field-level data model: messages, enums, constraints — resolve swagger `$ref` names here |
| `source_code`  | `srvs/**/*.go` + `libs/**/*.go` (hand-written; tests, mocks, generated `.pb.go` excluded) | Handler/proc/validation logic, chunked by Go declaration |

Every chunk is tagged with the git **branch** it was indexed from (provenance),
so multiple branches can coexist in one collection and searches can be filtered to
a specific build. `kb_info` reports branch/commit/timestamp per indexed version.

## Prerequisites

| Dependency | Install guide | Notes |
|------------|--------------|-------|
| Python 3.9+ | [python.org/downloads](https://www.python.org/downloads/) | Required to create the `.venv` |
| Qdrant | [qdrant.tech/documentation/guides/installation](https://qdrant.tech/documentation/guides/installation/) | Must be running at `localhost:6333` before setup |
| Docker *(recommended for Qdrant)* | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) | Easiest way to run Qdrant: `docker run -p 6333:6333 qdrant/qdrant` |
| Ollama | [ollama.com/download](https://ollama.com/download) | Must be running; setup pulls `nomic-embed-text` automatically |
| ZedCloud repo | — | Cloned locally at `~/git/zedcloud`, or set `GITHUB_TOKEN` to index from GitHub instead |

## Setup

```bash
cd zedcloud-kb-rag
./setup.sh
# or with a custom path:
./setup.sh --zcloud-path /path/to/zedcloud
```

Setup installs the Python venv, writes `config.json`, installs the `zcloud-kb` skill,
and registers the MCP server in `~/.mcp.json`.

## Indexing

**From a local clone:**
```bash
source .venv/bin/activate
python indexer/index.py --zcloud-path ~/git/zedcloud
```

**From GitHub (no local clone needed):**
```bash
source .venv/bin/activate
export GITHUB_TOKEN=<your-token>
python indexer/index.py --source github
```

Options:
- `--reset` — wipe and rebuild the collection (use after major repo changes)
- `--branch <name>` — GitHub branch to index (default: `main`)
- `--skip-swagger` — skip swagger endpoint indexing
- `--skip-protos` — skip proto indexing
- `--skip-source` — skip Go source indexing (the largest/slowest part)

First run takes ~10-20 minutes depending on machine speed.

## MCP Tools

| Tool               | Description                                    |
|--------------------|------------------------------------------------|
| `kb_info`          | Collection status, provenance (branch/commit/when), chunk counts |
| `search_zcloud_kb` | Hybrid semantic + keyword search               |
| `read_zcloud_file` | Read file from local clone (or GitHub fallback) by line range |

### Agent-ready output (`format="json"`)

`search_zcloud_kb` and `read_zcloud_file` default to `format="markdown"` (human-readable).
Pass `format="json"` for a structured envelope an orchestration agent can consume directly:

```json
{
  "kb": "zcloud", "query": "...", "doc_type": "all", "version": "main",
  "count": 3, "warnings": [],
  "results": [
    { "rank": 1, "score": 0.83, "doc_type": "source_code",
      "source": "srvs/seine/appinstproc.go", "section": "func validateAppInstance",
      "version": "main", "start_line": 142, "end_line": 210, "excerpt": "...",
      "fetch": { "tool": "read_zcloud_file",
                 "args": { "path": "srvs/seine/appinstproc.go", "start_line": 142, "end_line": 210 } } }
  ]
}
```

- `fetch` is the machine-readable follow-up action (replaces the prose "→ call read_..." hint).
- `swagger_docs` results carry a typed `api` block with the (unresolved) operation JSON.
- The envelope shape is identical across the eve-kb and zcloud-kb servers, discriminated by
  the `kb` field, so a multi-KB agent consumes both uniformly.

## Usage in Claude Code

After setup and indexing, restart Claude Code. The `zcloud-kb` skill activates automatically
when you ask about ZedCloud services, proto messages, or implementation details.

Example queries:
- "How does seine handle edge-node configuration?"
- "What proto message does gilas use for app instance creation?"
- "Show me the thames attestation flow"
- "What does the brazos kafka consumer do?"
