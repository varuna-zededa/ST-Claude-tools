# zcloud-mcp — ZedCloud API MCP Server

FastMCP server that exposes 40+ ZedCloud API tools to Claude Code via the MCP protocol.
Query and manage ZedCloud resources — edge nodes, applications, networks, IAM, Kubernetes
clusters — through natural language without writing API calls by hand.

## Why this exists

ZedCloud has a large API surface across 17+ services. Finding the right endpoint,
constructing the right query, and interpreting paginated results takes time even for
engineers who know the platform well. This server pre-wires all of it:
each tool handles auth, URL construction, pagination defaults, and response shaping.
Claude Code asks a question; the MCP server calls the API and returns a structured result.

Three concrete use cases drove the design:
1. **Fleet inspection** — "which edge nodes are offline?" calls the node summary API and
   returns a filtered, human-readable list without exposing 40-field JSON blobs
2. **Incident triage** — "show me error events for app X on device Y in the last hour"
   constructs the correct paginated event query and returns formatted results
3. **Test plan execution** — integrated with `/st-testplan-generator` to verify live
   ZedCloud state against expected API responses during black-box system tests

## Architecture

```
Claude Code
    │  MCP (streamable-http)
    ▼
FastMCP server  :8000/mcp
    │
    ├── auth.py          Bearer token extracted from x-zedcloud-authorization header
    ├── utils.py         Shared httpx client, URL builder, response limiter
    ├── <domain>.py      One file per API domain (40+ tool functions)
    └── mocks/           Pre-recorded JSON responses for offline development
```

- **Transport**: `streamable-http` on `0.0.0.0:8000/mcp`
- **Auth**: per-request Bearer token forwarded from the MCP caller's HTTP header
- **HTTP**: shared `httpx.AsyncClient` with 30 s timeout — one connection pool for the
  server's lifetime
- **Mock mode**: set `USE_MOCK_API_MCP_DATA=true` to serve responses from `mocks/*.json`
  without hitting the live API

## Tool categories

### IAM / Access Control
| Tool module | What it covers |
|-------------|---------------|
| `users.py` | List, search, and retrieve user accounts |
| `roles.py` | RBAC role definitions and assignments |
| `enterprises.py` | Enterprise (tenant) records — list, get by id/name, self |
| `sessions.py` | Active session inspection |
| `realms.py` | Authentication realm configuration |
| `entitlements.py` | Feature entitlement records |
| `authorization_profiles.py` | Authorization profile management |
| `document_policies.py` | Document-level access policies |

### Edge Infrastructure
| Tool module | What it covers |
|-------------|---------------|
| `edge_nodes.py` | Node fleet — list, get, events, metrics, EVE distribution summary |
| `edge_node_clusters.py` | Multi-node cluster definitions |
| `networks.py` | Network configurations |
| `network_instances.py` | Network instance state |
| `datastores.py` | Datastore definitions |

### Applications
| Tool module | What it covers |
|-------------|---------------|
| `edge_apps.py` | Edge application bundle catalog |
| `global_edge_apps.py` | Global (marketplace) app bundles |
| `edge_app_instances.py` | Running app instances — status, events, logs, metrics |
| `app_profiles.py` | Application configuration profiles |
| `profile_deployments.py` | Profile deployment records |

### Projects & Deployments
| Tool module | What it covers |
|-------------|---------------|
| `projects.py` | Project definitions and membership |
| `deployment_projects.py` | Deployment project records |
| `images.py` | EVE OS base image catalog |
| `brands.py` | Hardware brand catalog |
| `sysmodels.py` | Hardware system model catalog |
| `artifacts.py` | Binary artifact store |

### Kubernetes / ZKS Services
| Tool module | What it covers |
|-------------|---------------|
| `zks_instances.py` | ZKS cluster instances |
| `cluster_instances.py` | Cluster instance state |
| `cluster_groups_zks.py` | ZKS cluster groups |
| `secrets_zks.py` | ZKS secrets (credential values redacted in responses) |
| `kubernetes_deployments_zks.py` | Kubernetes deployment records |
| `helm_charts_zks.py` | Helm chart catalog |
| `gitrepos_zks.py` | Git repository integrations |
| `private_repository_zks.py` | Private container registry credentials |

### Data & Observability
| Tool module | What it covers |
|-------------|---------------|
| `datastreams.py` | Data stream configurations |
| `volume_instances.py` | Volume instance state |
| `asset_groups.py` | Asset group definitions |
| `third_party_plugins.py` | Third-party plugin registrations |
| `azure_deployments.py` | Azure-side deployment records |
| `api_usage_tracking.py` | API usage statistics |
| `metrics.py` | Prometheus `/metrics` endpoint |

### Utilities
| Tool module | What it covers |
|-------------|---------------|
| `datetime_utils.py` | Time range helpers used by event/log queries |

## Prerequisites

- Python 3.12+
- A ZedCloud account with an API bearer token
- Network access to your ZedCloud controller

## Setup (one-time)

```bash
cd path/to/zcloud_mcp
chmod +x setup.sh
./setup.sh
```

`setup.sh` will:
1. Create a Python 3.12 virtual environment in `.venv/`
2. Install all dependencies from `pyproject.toml`
3. Copy `.env.example` → `.env` and prompt you to fill in credentials
4. Register the MCP server in `~/.mcp.json` so Claude Code can connect to it

After setup, edit `.env`:

```bash
ZEDCLOUD_BASE_URL=https://zedcontrol.zededa.net   # your controller hostname
ZEDCLOUD_BEARER_TOKEN=your_bearer_token_here
USE_MOCK_API_MCP_DATA=false
```

## Running the server

```bash
./start.sh
```

The server starts on `http://0.0.0.0:8000/mcp`. Health check: `GET /v1/health`.

To run in the background:
```bash
nohup ./start.sh > zededa_mcp.log 2>&1 &
```

## Docker

```bash
# Build
docker build -t zcloud-mcp .

# Run
docker run -p 8000:8000 \
  -e ZEDCLOUD_BASE_URL=https://zedcontrol.zededa.net \
  -e ZEDCLOUD_BEARER_TOKEN=your_token \
  zcloud-mcp
```

## Claude Code integration

Once the server is running and registered in `~/.mcp.json`, Claude Code connects
automatically. No slash command is needed — the tools are available by name.

To verify the connection from Claude Code:
```
check /v1/health on the zcloud mcp server
```

### Passing your bearer token

The server reads the caller's token from the `x-zedcloud-authorization` HTTP header
on each MCP request. Claude Code sets this header when you configure it:

In `~/.mcp.json`:
```json
{
  "mcpServers": {
    "zcloud_mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "x-zedcloud-authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

Or set `ZEDCLOUD_BEARER_TOKEN` in `.env` to use a server-side default token
(useful for single-user deployments).

## Mock mode

Set `USE_MOCK_API_MCP_DATA=true` in `.env` to serve pre-recorded responses from
`mocks/*.json`. No live API calls are made. Useful for:
- Local development without a ZedCloud account
- Offline demos
- Unit testing

Mock files follow the naming convention `<resource-type>-list.json` (collections)
and `<resource-type>-detail.json` (single objects). See `mocks/README.md` for details.

## Response limits

To stay within LLM context budgets, the server enforces:
- **8 000 character** max per tool response
- **10 items** max per list response

Use pagination parameters (`page_size`, `page_num`) or name/ID filters to retrieve
specific records when a list is truncated.

## Configuration reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZEDCLOUD_BASE_URL` | Yes | — | ZedCloud controller base URL |
| `ZEDCLOUD_BEARER_TOKEN` | No | — | Default bearer token (overridden per-request) |
| `USE_MOCK_API_MCP_DATA` | No | `false` | Serve mock data instead of live API |

## Development

```bash
# Install with test extras
pip install -e ".[test]"

# Run tests
make test

# Run specific test file
python3 -m pytest tests/test_auth.py -v

# Lint
make lint
```

See `tests/README_TESTS.md` for the full test strategy and mock patterns.
