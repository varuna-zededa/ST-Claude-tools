---
name: zcloud-kb
description: >
  Search the ZedCloud knowledge base for API endpoint schemas, service behavior,
  and feature documentation to help test engineers understand what to test and how.
  Use when someone asks what API to call for a feature, what request/response fields
  look like, how a service is supposed to behave, or needs context to write test cases.
  Trigger phrases: "what API", "which endpoint", "how do I test", "what does seine do",
  "what does gilas do", "how does indusv2 work", "what fields does", "expected response",
  "what happens when", "what does zedcloud do when", "test this feature",
  "zcloud API for", "how does service behave", "what service handles",
  "swagger for", "endpoint for", "request body for", "response schema".
---

# ZedCloud Knowledge Base Skill

You have three MCP tools available:
- `kb_info` — show collection status and chunk counts by doc_type
- `search_zcloud_kb` — hybrid search over API docs, service docs, and source code
- `read_zcloud_file` — read a file from the ZedCloud repo at a specific line range

## MCP availability check — do this first

Before answering, check whether `search_zcloud_kb` is available in this session.

**If `search_zcloud_kb` IS available:** use it. Do not answer from general knowledge.

**If `search_zcloud_kb` is NOT available:** start your response with:

> ⚠️ **Unverified answer** — the zcloud-kb MCP server is not running in this session.
> Information below is based on general knowledge, not verified against the ZedCloud codebase.
> For verified answers: restart Claude Code to activate the MCP server, then re-ask.

## Two-phase workflow (when MCP is available)

### Phase 1 — always start here

Call `search_zcloud_kb`. For test-engineering questions, lead with `doc_type="swagger_docs"`
when the question is about an API call, or `doc_type="service_docs"` when it is about
what a service does. Fall back to `doc_type="all"` if you need broader context.

If the first query returns thin results, re-query with:
- The service name (seine, gilas, indusv2, ganges, thames, purus, etc.)
- The resource name (device, app-instance, user, network, cluster, etc.)
- The action (create, delete, onboard, attest, configure, deploy)

### Phase 2 — for source_code and proto_defs results

When `search_zcloud_kb` returns a `source_code` or `proto_defs` result and you need
the full function/message body, follow the `read_zcloud_file()` hint. For test
engineers this answers: "what does the API reject?", "what are the required fields?",
"what side effects does this call trigger?", "what enum values are valid?"

## doc_type filter guide

| doc_type       | When to use                                                  |
|----------------|--------------------------------------------------------------|
| `swagger_docs` | Finding the right endpoint, request body, response schema    |
| `service_docs` | Understanding what a service does and its data flow          |
| `zcloud_docs`  | Feature design, architecture, how things fit together        |
| `proto_defs`   | Field-level data model: message fields, enums, constraints. **Resolve swagger `$ref` names here** (e.g. a body `#/definitions/AppInstance` → search proto_defs for the `AppInstance` message) |
| `source_code`  | What the API validates/rejects, what a call triggers — now covers all hand-written `srvs/**` and `libs/**` Go (handlers, proc, validation), not just entrypoints |
| `library_docs` | Shared library READMEs (sparse)                              |

## Output format

Both `search_zcloud_kb` and `read_zcloud_file` default to human-readable markdown.
When you (or a downstream agent) need to parse results programmatically, pass
`format="json"` — you get an envelope `{kb, query, doc_type, version, count, warnings,
results[]}` where source/proto results include a machine-readable `fetch` action and
swagger results include a typed `api` block. Use json mode when chaining tool calls or
building structured artifacts; use markdown when answering a person.

## Versions (provenance)

The KB tags every chunk with the git branch it was indexed from. Call `kb_info`
to see which branch/commit/timestamp is indexed. When analyzing a failure against
a specific build, pass `version="<branch>"` to `search_zcloud_kb` so answers match
the code under test rather than mixing branches.

## Response format for test engineers

**For API / endpoint questions:**

**Endpoint:** `METHOD /path`
**Service:** source name
**Summary:** ...

**Request body** (required fields):
```json
{ ... key fields from full_operation ... }
```

**Success response:** HTTP status + key fields
**Error cases:** what returns 4xx and why (from source_code if needed)

**To test this:**
- Happy path: [what a passing call looks like]
- Negative cases: [missing fields, bad values, unauthorized]

**Source:** `<file from KB result>`

---

**For "how does service X behave" questions:**

**Service:** name
**Purpose:** [from service_docs chunk]
**Data flow:** [how requests enter and exit this service]

**What to verify in tests:**
- [observable API behavior / state changes]
- [related endpoints to check side effects]

**Source:** `<file from KB result>`

## ZedCloud service → API ownership

| Service   | Owns these APIs                                    |
|-----------|----------------------------------------------------|
| gilas     | All external REST APIs (gateway → kafka → service) |
| seine     | Edge node config: devices, apps, networks, volumes |
| indusv2   | Users, roles, auth, enterprise management          |
| ganges    | Metrics queries                                    |
| thames    | Device attestation and enrollment                  |
| purus     | DeviceTwin / device shadow config                  |
| k3s-orchestration | Kubernetes cluster management               |
| niles     | Datastore upload/download                          |
| workflow-manager / workflow-executor | Workflow APIs        |

## Integration with test plan generation

When the `st-testplan-generator` skill is active, use `search_zcloud_kb` to:
- Look up request/response schemas for API test cases (swagger_docs)
- Confirm expected service behavior for preconditions and assertions (service_docs)
- Find what the API validates to design meaningful negative test cases (source_code)

Results feed directly into Section 3 (API Test Cases) of the test plan.
