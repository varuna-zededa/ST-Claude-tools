# eve-knowledge-base — EVE OS Knowledge Base for Claude Code

Token-efficient semantic search over EVE OS documentation and source code, wired into Claude
Code as an MCP server and skill. Ask natural-language questions about EVE CLI commands,
debugging steps, pillar agent behavior, or expected device state — without re-parsing the
1.12 GB repo each session.

## Why this exists

Testing EVE OS features requires running specific CLI commands on the device over SSH —
checking pillar agent state, inspecting pubsub paths, reading logs. There is no single
reference for these commands. The EVE repo is 1.12 GB with 50,000+ files, far too large
to load into a Claude Code session. The result: test engineers had to ping developers
every time they needed a device-side verification command, slowing down both sides.

This tool solves that by pre-indexing the parts of the repo that matter for testing —
docs, per-agent design docs, and pillar agent source — into a local Qdrant vector database.
Claude Code queries it on demand via an MCP server. A search over 3100 indexed chunks
costs a fraction of a token budget compared to parsing the full repo, and the answers
are sourced directly from EVE documentation and source code rather than general knowledge.

Three concrete use cases drove the design:
1. **Finding device commands** — "what command checks NIM's selected uplink?" returns the
   exact EVE CLI command with expected output, sourced from pillar docs or agent source
2. **Verifying behavior from code** — when a test fails, search for what the relevant agent
   is supposed to do and compare against what you observe on the device
3. **Generating test plans** — integrated with `/st-testplan-generator` to automatically
   produce EVE device test cases (EVE CLI commands, pubsub paths, expected state) alongside
   the ZedCloud API test cases, from the same source documents

## What gets indexed

| Source | doc_type | Content |
|--------|----------|---------|
| `eve/docs/` (75 files) | `eve_docs` | All EVE design and operational docs |
| `eve/pkg/pillar/docs/` (23 files) | `pillar_docs` | Per-agent implementation docs |
| `eve/pkg/edgeview/README.md` | `edgeview` | EdgeView remote debugging reference |
| `eve/CLAUDE.md` | `eve_docs` | Repo architecture overview |
| `eve/pkg/pillar/cmd/*/` (35 agents) | `source_code` | Pillar agent entrypoints (run.go or `<agent>.go`) |

Total: ~3100 chunks stored in Qdrant (`eve_kb` collection). Nothing leaves your machine.

## How search works

Two mechanisms run in parallel on every query and results are merged by score:

1. **Dense vector search** — semantic similarity via `nomic-embed-text` embeddings (768-dim, cosine distance)
2. **Keyword search** — exact `MatchText` on significant query terms against a Qdrant text payload index

This hybrid catches both conceptually-similar results and exact EVE-specific terms (agent
names, flag names, pubsub paths) that vector search alone sometimes misses.

## Two-phase retrieval for source code

Source code results include only a 6-line excerpt — the actual function spans many more lines.
When `search_eve_kb` returns a `source_code` result, the response includes a
`read_eve_file(path, start_line, end_line)` hint. **Always follow it.** The `read_eve_file`
tool reads the full line range from your local EVE clone (or falls back to GitHub if not found).

Documentation results (`eve_docs`, `pillar_docs`, `edgeview`) are self-contained — use the
chunk text directly.

## MCP tools

| Tool | What it does |
|------|-------------|
| `kb_info()` | Shows chunk counts by doc_type, Qdrant URL, EVE path, and re-index command |
| `search_eve_kb(query, doc_type, top_k)` | Hybrid search — returns docs inline, source_code as excerpt + `read_eve_file` hint |
| `read_eve_file(path, start_line, end_line)` | Reads a file from local EVE clone; GitHub fallback if not found locally |

## Prerequisites

- Python 3.10+
- [Qdrant](https://qdrant.tech/) running on `localhost:6333`
- [Ollama](https://ollama.com/) with `nomic-embed-text` pulled

```bash
ollama pull nomic-embed-text
```

## Install (one-time per team member)

```bash
git clone <this-repo> ~/git/eve-kb
cd ~/git/eve-kb
chmod +x setup.sh
./setup.sh --eve-path ~/git/eve    # default: ~/git/eve
```

`setup.sh` creates a Python venv, installs dependencies, writes `config.json`, installs the
Claude Code skill to `~/.claude/skills/eve-kb/`, and registers the MCP server in
`~/.claude/settings.json`.

**Restart Claude Code** after setup to load the MCP server.

## Index EVE docs and source

Choose the mode that fits your setup:

### From GitHub (no local EVE clone needed)

```bash
source .venv/bin/activate

# Index master branch
python indexer/index.py --source github

# Index a specific release branch
python indexer/index.py --source github --branch eve-9.13
```

### From a local EVE clone

```bash
source .venv/bin/activate
python indexer/index.py --source local --eve-path ~/git/eve
```

## Update for a new EVE release

```bash
source .venv/bin/activate

# GitHub
python indexer/index.py --source github --branch eve-9.13 --reset

# Local clone
python indexer/index.py --source local --eve-path ~/git/eve --reset
```

`--reset` wipes and rebuilds the collection cleanly. Run `kb_info()` in Claude Code to verify
chunk counts afterward.

## Usage in Claude Code

The skill loads automatically when your query contains EVE-specific phrases:

| Trigger phrase | Example query |
|----------------|---------------|
| `on EVE`, `EVE command`, `EVE CLI` | "give me commands to check network status on EVE" |
| `pillar agent`, `zedagent`, `domainmgr` | "what does domainmgr do when a VM fails to start?" |
| `nim agent`, `baseosmgr`, `zedrouter` | "how does nim select a management port?" |
| `debug EVE`, `ssh into EVE` | "how do I debug app deployment failure on EVE?" |
| `pubsub path`, `eve device command` | "what pubsub path does volumemgr write to?" |
| `edgeview` | "run an edgeview query for network stats" |
| `eve verification steps` | "add EVE verification steps to this test plan" |

You can also invoke the skill directly:

```
/eve-kb
```

### If the MCP server is not reachable

If Qdrant or the MCP server isn't running, the skill answers from Claude's general EVE
knowledge and leads the response with:

> ⚠️ **Unverified answer** — the eve-kb MCP server is not running in this session.

This happens when Claude Code was open before the MCP was registered, or Qdrant isn't running.
Fix: ensure Qdrant is running, then restart Claude Code.

```bash
# Check Qdrant
curl http://localhost:6333/healthz
```

## Integration with st-testplan-generator

When generating a test plan with `/st-testplan-generator` for a feature that touches EVE
device behavior, the skill automatically:

1. Calls `search_eve_kb` for device-side commands relevant to the feature
2. Follows up with `read_eve_file` for source code context
3. Injects an **"EVE Device Verification Steps"** block into each relevant test case:

```
**EVE Device Verification (SSH into device):**
```bash
ssh root@<device-ip>
<command from KB>
```
Expected: <healthy state from KB>
Pubsub path: /run/<agent>/<topic>/*.json
```

No extra steps needed — both skills are loaded together and coordinate automatically.

## Team sharing

Each team member:
1. Installs Qdrant + Ollama locally
2. Clones this repo and runs `./setup.sh`
3. Indexes EVE docs: `python indexer/index.py --source local --eve-path ~/git/eve`
4. Restarts Claude Code

The Qdrant knowledge base is local to each machine. The MCP server is a lightweight stdio
process spawned by Claude Code on demand — no background service needed.

## config.json

Written by `setup.sh`. Edit directly to change paths:

```json
{
  "eve_path": "/Users/you/git/eve",
  "qdrant_url": "http://localhost:6333"
}
```

`eve_path` is used by `read_eve_file` for local file reads. If the file isn't found locally,
it falls back to `raw.githubusercontent.com/lf-edge/eve/master/<path>`.
