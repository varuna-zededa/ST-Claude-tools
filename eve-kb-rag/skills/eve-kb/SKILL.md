---
name: eve-kb
description: >
  Search the EVE OS knowledge base for internal CLI commands, debugging steps, and behavior
  verification. Use when the user asks about EVE commands to verify a feature, how to debug
  something on an EVE device, what a pillar agent does, expected EVE behavior when a test fails,
  or wants EVE-specific verification steps in a test plan.
  Trigger phrases (must be EVE-specific, not general): "EVE command", "on EVE", "debug EVE",
  "what does EVE do", "pillar agent", "EVE CLI", "ssh into EVE", "eve verification steps",
  "eve debug", "eve edgeview", "pillar source", "zedagent", "domainmgr", "nim agent",
  "baseosmgr", "zedrouter", "volumemgr", "pubsub path", "eve device command".
---

# EVE OS Knowledge Base Skill

You have two MCP tools available:
- `search_eve_kb` — hybrid search (vector + keyword) over indexed docs and source code
- `read_eve_file` — read a file from the EVE repo at a specific line range

## MCP availability check — do this first

Before answering, check whether `search_eve_kb` is available as a tool in this session.

**If `search_eve_kb` IS available:** use it. Do not answer from general knowledge.

**If `search_eve_kb` is NOT available:** start your response with this exact block:

> ⚠️ **Unverified answer** — the eve-kb MCP server is not running in this session.
> Commands below are based on general EVE OS conventions, not sourced from the knowledge base.
> For verified commands: restart Claude Code to activate the MCP server, then re-ask.

Then provide your best answer using EVE conventions. Never bury this warning at the end.

## Two-phase workflow (when MCP is available)

### Phase 1 — always start here
Call `search_eve_kb` with a focused natural language query.

If the first query returns thin or irrelevant results, try a second call with
different phrasing — use the agent name (nim, zedagent, domainmgr), the EVE
term (pubsub, zedbox, pillar), or the action (deploy, mount, attestation).

### Phase 2 — only for source_code results
When `search_eve_kb` returns a result with `doc_type = source_code`, the response
includes a `read_eve_file(path, start_line, end_line)` hint. **Always follow it.**
Source code chunks are 1200-char excerpts — the full function context is in the file.

For `eve_docs` and `pillar_docs` results: use the chunk text directly as the answer.
Those sections are self-contained and reading the full file adds nothing.

## Response format

Structure your answer as:

**What to check:**
<the specific state or condition relevant to the test>

**Command (run via SSH on EVE device):**
```bash
# Connect: ssh root@<device-ip>  (or: ssh -p 2222 root@localhost for QEMU)
<exact command>
```

**Expected output (passing):**
<what healthy/correct state looks like>

**If failing — where to dig:**
- Pubsub state files on device: `/run/<agent>/<topic>/*.json` or `/persist/status/<agent>/`
- Relevant edgeview query (if applicable)

**Source:** `<file from KB result>`

## EVE pubsub paths (always relevant for debugging)

Every pillar agent writes state to disk:
- Ephemeral: `/run/<agent>/<topic>/*.json`
- Persistent: `/persist/status/<agent>/...`
- Global config: `/run/global/`

Common agents: `zedagent` `zedmanager` `zedrouter` `domainmgr` `nim`
`baseosmgr` `volumemgr` `downloader` `verifier` `nodeagent` `tpmmgr`

## Integration with test plan generation

When the `st-testplan-generator` skill is active and the feature has EVE device-side
behavior to verify, call `search_eve_kb` to source exact commands and expected output
for the **EVE Device Test Cases** section (Section 4 of the test plan).

EVE commands must never appear in API test cases (Section 3) — only in the separate
EVE section and its corresponding `-eve-testcases.csv`.
