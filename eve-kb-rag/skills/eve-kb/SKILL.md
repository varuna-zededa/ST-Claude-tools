---
name: eve-kb
description: >
  Search the EVE OS knowledge base for internal CLI commands, debugging steps, and behavior
  verification. Use when the user asks about EVE commands to verify a feature, how to debug
  something on an EVE device, what a pillar agent does, expected EVE behavior when a test fails,
  or wants EVE-specific verification steps in a test plan.
  Trigger phrases (must be EVE-specific, not general): "EVE command", "on EVE", "debug EVE",
  "what does EVE do", "pillar", "EVE CLI", "ssh into EVE", "eve verification steps",
  "eve debug", "eve edgeview", "pubsub path", "eve device command",
  "how to verify on EVE", "expected EVE behavior", "what should EVE show".
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
For test engineers, this is how you find: exact CLI flag names, the values an agent
accepts, what conditions trigger a state change, and what observable output to expect.

For `eve_docs` and `pillar_docs` results: use the chunk text directly as the answer.

### Output format

Both `search_eve_kb` and `read_eve_file` default to human-readable markdown. When you
(or a downstream agent) need to parse results programmatically, pass `format="json"` —
you get an envelope `{kb, query, doc_type, version, count, warnings, results[]}` where
`source_code` results include a machine-readable `fetch` action. The envelope shape is
identical to the zcloud-kb server (discriminated by `kb`). Use json when chaining tool
calls; use markdown when answering a person.
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

**If it fails — capture diagnostics and file a bug:**
- On the device, run EVE's `collect-info.sh` to produce a
  `collect-info-<timestamp>.tar.gz` (logs + device state). If unsure of the exact
  invocation on this build, confirm it via `search_eve_kb`.
- File the bug with: the command run, actual vs expected output, EVE/device version,
  and the tarball attached. Hand off to dev for root-cause.
- Do **not** dig into pubsub state, raw logs, or edgeview yourself — that is dev work
  once they have the tarball. Keep test-engineer scope to: verify via CLI, then collect-info.

**Source:** `<file from KB result>`

## Diagnostics handoff — collect-info

The test-engineer scope on EVE is narrow: **run CLI commands to verify behavior, and
when a command reveals a bug, capture diagnostics with `collect-info.sh` and ship the
resulting `collect-info-<timestamp>.tar.gz` to development** with the bug description.

Inspecting pubsub state (`/run/<agent>/...`), reading raw logs, or running edgeview
queries is **out of scope** — the collect-info tarball gives dev everything needed for
that. Don't instruct the tester to do dev-side debugging.

Pillar subprocesses you may name in CLI verification: `zedagent` `zedmanager`
`zedrouter` `domainmgr` `nim` `baseosmgr` `volumemgr` `downloader` `verifier`
`nodeagent` `tpmmgr` (all run under `pillar`).

## Pointing dev at the right logs (for the bug report)

The tester does **not** read logs — but naming the relevant **log source** in the bug
report lets dev grep the collect-info tarball fast. EVE has no per-service log file; all
pillar agents log through `newlogd` into bundled gzips:

- On device / in the tarball: `/persist/newlog/` (`collect/`, `devUpload/`, `appUpload/`,
  `keepSentQueue/`, `failedUpload/`) — device logs `dev.log.<ts>.gz`, app logs
  `app.<uuid>.log.<ts>.gz`.
- Logs are isolated by the **`source` field = agent name** (plus `pillar.out` / `pillar.err`
  for unparseable pillar lines).
- Levels follow EVE conventions: **Error** (object / internal errors), **Warning**
  (resource issues), **Notice** (pubsub object events). Point dev at Error/Warning first.

**To find which agent(s) own a feature, query the KB live — do not hardcode:**
`search_eve_kb("<feature> agent responsible", doc_type="pillar_docs")`.
A few common mappings as a sanity check (always confirm/expand via the KB):

| Feature area        | Log source(s)                          |
|---------------------|----------------------------------------|
| Networking / DHCP   | `nim`, `zedrouter`                     |
| App deploy / run    | `zedmanager`, `domainmgr`, `volumemgr` |
| Config / controller | `zedagent`                             |
| Attestation / TPM   | `tpmmgr`, `attest`                     |
| Base OS update      | `baseosmgr`, `nodeagent`               |
| Image download      | `downloader`, `verifier`               |

Add to the bug report: the relevant `source=<agent>` and level, so dev can locate the
failure in the tarball without hunting. This stays within tester scope — you are
*naming* the source, not reading the logs yourself.

## Integration with test plan generation

When the `st-testplan-generator` skill is active and the feature has EVE device-side
behavior to verify, call `search_eve_kb` to source exact commands and expected output
for the **EVE Device Test Cases** section (Section 4 of the test plan).

EVE commands must never appear in API test cases (Section 3) — only in the separate
EVE section and its corresponding `-eve-testcases.csv`.

Each EVE test case's failure path should be **"run collect-info and file a bug with the
tarball"** — never device-side debugging steps, which are out of test-engineer scope.
