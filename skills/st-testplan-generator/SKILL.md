---
name: st-testplan-generator
description: >
  Generates comprehensive black-box system test plans for cloud and EVE OS features. Use this
  skill whenever the user wants to create a test plan, test cases, or testing documentation for
  a new or changed feature — even if they say "generate testcases", "write a testplan", "help me
  test this feature", "create NFR testcases", "I need API tests for this PR", or just paste a
  Jira ticket and ask what to test. Also trigger when the user provides a GitHub PR, merge commit,
  Jira ticket, or spec document and asks what needs to be tested. Produces a structured .md test
  plan and one or two ready-to-import .csv files: one for API/ZedCloud test cases, and a separate
  one for EVE device test cases if EVE-specific verification is needed. API test cases are verified
  entirely through ZedCloud API calls — no direct EVE API calls, no device-side steps in API TCs.
  EVE test cases use EVE CLI commands run on the device and are sourced from EVE PR test steps or eve-kb queries.
---

# Test Plan Generator — ZedCloud API + EVE Device

You are generating a professional **black-box system test plan** written for a **system test
team** — not for developers.

There are two distinct tracks, and they must never be mixed:

**Track 1 — ZedCloud API test cases**
All verification is done through ZedCloud API calls only. Configuration is applied via API
(POST/PUT), and verification is done via GET calls and ZedCloud status fields. There are no
EVE CLI commands, no EVE device checks, no pubsub paths in API test cases — ever.

**Track 2 — EVE device test cases** (only if triggered — see Phase 2)
Verification is done by SSHing into the EVE device and running commands. Steps come from
EVE PR test descriptions or eve-kb queries. Generated only when source documents explicitly
describe device-side behavior to verify.

This is a two-phase workflow: **collect** then **generate**. Work through both phases carefully.

---

## Phase 1: Document Collection

Ask the user for each of the following documents. Present them as a numbered list and make clear
that **none are mandatory** — they should share whatever they have.

1. **Jira PM ticket** — product/business requirements (e.g. `PM-532`)
2. **Jira NFR / CI ticket** — engineering NFR or CI ticket (e.g. `NFR-170`)
3. **PRD** — product requirements document (URL or text)
4. **Cloud functional spec** — API design doc, Google Doc, Confluence page, etc.
5. **EVE functional spec** — EVE-side design doc if the feature touches the edge agent (optional)
6. **ZedCloud Pull Request or merge commit** — GitHub PR URL or commit hash from the ZedCloud repo
7. **EVE Pull Request or merge commit** — GitHub PR URL or commit hash from the EVE repo (optional)
8. **Feature validation workflow** — a high-level, ordered list of steps describing how the
   feature should be validated end-to-end. This is the tester's mental model of the happy path,
   not a formal test case. Example:
   ```
   1. Configure <X> on the device via ZedCloud API
   2. Verify the configuration is accepted and reflected in a GET response
   3. Trigger the action or condition that exercises the feature
   4. Confirm the expected system behavior is observable via ZedCloud status/GET
   5. Clean up / tear down the configuration
   ```
   If they cannot provide one, ask them to describe in plain English how they would manually
   validate that the feature is working correctly.

After the user responds, confirm what was provided. Then in a single follow-up message ask both:
1. "What folder name should I use for the CSV Folder field? (e.g. `Cloud/NFR-170-LAG-support`)"
2. "Is there any other context to factor in — constraints, related features, areas of concern?"

If the user already provided the folder value earlier in their message, skip that question.
Wait for this response before starting research.

---

## Phase 2: Deep Research

Read every document the user provided. Be thorough — skim nothing.

### Fetching Jira tickets
Use the Atlassian MCP tools (`getJiraIssue`, `searchJiraIssuesUsingJql`) if available.
Otherwise open the ticket URL in the browser.

### Fetching Google Docs / Confluence pages
- **Google Docs**: If the normal edit URL fails or renders as a canvas, switch to the
  `mobilebasic` endpoint:
  `https://docs.google.com/document/d/<DOC_ID>/mobilebasic`
- **Confluence**: Use `getConfluencePage` MCP tool if available, otherwise fetch via browser.

### ZedCloud KB lookup (cross-check and gap-fill)

After reading all user-provided documents, query the ZedCloud knowledge base using
`search_zcloud_kb` to cross-check and supplement the API and implementation information
the user has given you.

**Step 1 — Cross-check: flag differences**

Call `search_zcloud_kb` with the feature name, relevant endpoint paths, or service names
(e.g. `"LAG network instance API"`, `"device uplink configuration"`, `"seine service behavior"`).
For any result with a `source_code` or document reference, call `read_zcloud_file` to read
the full content.

Compare KB output against what the user's documents describe. If there are discrepancies —
different field names, different enum values, missing validation rules, conflicting behavior —
**flag them explicitly to the user before generating the test plan**. Format as:

> **ZedCloud KB discrepancy noticed:**
> - *In your documents:* `<what the user doc says>`
> - *In zcloud-kb:* `<what the KB says>`
> - Impact on test cases: `<which TCs or scenarios are affected>`

Ask the user to confirm which source is correct before proceeding.

**Step 2 — Gap-fill: supplement missing info**

If the user-provided documents are incomplete or missing detail for any part of the API surface
(e.g. a field is mentioned but not defined, an endpoint is referenced but its schema is
unclear), use `search_zcloud_kb` to retrieve the complete information.

When you fill a gap this way, tell the user clearly:

> **Additional info sourced from zcloud-kb** (not in your documents):
> - `<what was learned — endpoint schema, field definition, validation rule, etc.>`

This makes it transparent what came from the user and what was discovered through the KB.

If `search_zcloud_kb` returns no relevant results for a topic, note the gap in
**Section 6 References** of the test plan so testers know coverage is incomplete.

---

### Fetching ZedCloud PRs and commits
- For a PR diff: navigate to `https://github.com/<org>/<repo>/pull/<N>/files` in the browser.
- For a commit diff: fetch `https://github.com/<org>/<repo>/commit/<hash>.diff`.

**Skip these files entirely from ZedCloud PRs:**
- Files ending in `_pb2.py` — auto-generated Python protobuf bindings
- Files ending in `.pb.go` — auto-generated Go protobuf bindings
- Files ending in `.swagger.json` — auto-generated Swagger/OpenAPI
- Files named `*data.go` — DB struct definitions only
- Any file under `tests/`
- SQL migration files (`*.up.sql`, `*.down.sql`)

**Focus on these files for the ZedCloud API surface:**
- **`.proto` schema files** — new message types, fields, enums
- **`*proc.go`, `*handler.go`** — validation rules and error conditions visible at API level
- **Conversion / mapping logic** (e.g. `purus/`) — implicit API-level requirements
- **Cross-resource logic** (e.g. `netinstproc.go`) — interaction constraints

### Fetching EVE PRs
Read the PR description, commit messages, and changed files. Focus on:
- `pkg/pillar/cmd/*/` — pillar agent entrypoints (the main behavior source)
- `pkg/pillar/docs/` — per-agent design docs
- `docs/` — EVE-level design docs

**Skip auto-generated EVE files:** `*.pb.go`, `*_pb2.py`, `.swagger.json`

### What to extract from ZedCloud research
Combine `zcloud-kb` results with PR diff analysis. The KB is the primary source for stable
API documentation; the PR diff reveals what is *new or changed* in this feature.

- Complete API surface: all new/changed endpoints, fields, enums, request/response shapes
- Every validation rule → input condition + expected HTTP error code and message
- All enum values and their semantics
- Constraints and exclusivity rules
- Update / delete lifecycle rules
- Cross-resource interactions

### EVE flag: decide whether Track 2 is needed

After reading all documents, answer this question:
**Do any of the source documents explicitly describe device-side behavior that a tester must
verify on the EVE device itself?**

This is true if any document contains:
- Test steps that reference SSH, `logread`, pubsub paths, EVE CLI commands, or device state
- An EVE PR with test instructions in the PR description or commit messages
- An EVE functional spec describing observable device behavior

If **no** → generate only Track 1 (API test cases). Skip the EVE section entirely.
If **yes** → generate both tracks. Continue with the EVE research steps below.

### EVE research (only if EVE flag is set)

**Step 1 — Read and classify EVE PR steps**

**If an EVE PR was provided**, read the PR description and commit messages for test steps.
Classify each described step:

- **Already has exact commands** (e.g., `logread -f -t nim`, `cat /run/nim/DeviceNetworkStatus/*.json`):
  Do not use these as-is without validation. Call `search_eve_kb` to cross-check each command.
  If the KB describes the same step differently — different command, different pubsub path, or
  different expected output — flag it to the user before generating the test plan:

  > **EVE KB discrepancy noticed:**
  > - *In EVE PR:* `<command from PR>`
  > - *In eve-kb:* `<command or description from KB>`
  > - Affected test step: `<which step or scenario>`

  Ask the user to confirm which is correct before including the command in the test case.

- **Verbose text without commands** (e.g., "verify that nim selects the correct uplink after
  the primary interface fails"):
  Call `search_eve_kb` to find the exact commands. Follow up with `read_eve_file` for any
  `source_code` result. Use what the KB returns to fill in concrete commands and expected output.

**Step 2 — Proactive pillar agent lookup**

Identify which pillar agents are involved in the feature (from the PR, spec, or EVE KB results).
For each relevant agent (e.g. `nim`, `baseosmgr`, `zedmanager`, `domainmgr`), call
`search_eve_kb` with the agent name and the feature topic. This surfaces:
- Additional pubsub paths the PR may not have mentioned
- Related CLI commands useful for verifying healthy state
- Inter-agent interactions observable on device

Use these results to enrich test case steps beyond what the PR description alone provides.

**Step 3 — Expected output and healthy state**

For every EVE test step, explicitly query `search_eve_kb` for what *healthy state* looks like —
not just the command to run, but what the output should contain. For example:
- What fields appear in `/run/<agent>/<topic>/*.json` when the feature is working correctly?
- What does `logread` show when the pillar agent completes the action successfully?
- What is absent or different in the output when the feature is NOT working?

Use KB results to populate the **Expected Results** field of each EVE test case with concrete,
observable output rather than generic descriptions.

**If no EVE PR but EVE verification is needed from specs/docs:**
Call `search_eve_kb` with queries derived from what the docs say needs to be verified on device.
Apply Steps 2 and 3 above to enrich commands and expected output.

**Gap reporting**

If `search_eve_kb` returns no results for a step or agent topic, do not silently mark it TBD.
Report the gap explicitly to the user before generating the test plan:

> **EVE KB gap — no coverage found for:**
> - Topic searched: `<query used>`
> - Affected test steps: `<which steps have no confirmed command>`
> - Action needed: The tester will need to find or confirm the correct EVE CLI command manually.

Mark affected steps as `[TBD — verify command: <description of what needs to be confirmed>]`
so the tester knows exactly what to look up.

---

## Phase 3: Generate the .md Test Plan

Save the file as `<jira-ticket-or-feature-name>-testplan.md`.

### Document structure

```
# <Feature Name> Test Plan

**Jira References:** [links to tickets provided]
**Date:** <today's date>

---

## 1. Feature Overview
### 1.1 Background
### 1.2 Use Case / Customer Context
### 1.3 <Architecture / Data Model if relevant>
### 1.4 <Key Concepts — enums, modes, parameters, etc.>

---

## 2. ZedCloud API Changes
### 2.1 New or Changed Endpoints
### 2.2 New Fields and Object Structures  (with annotated JSON examples)
### 2.3 Enum Definitions
### 2.4 Validation Rules  (table: Rule # | Rule | Error Condition)

---

## 3. ZedCloud API Test Cases

### Prerequisites
[What the tester needs set up before starting — devices onboarded, projects created, etc.]

---

### TC-01: <Title>

**Objective:** <one sentence>

**Steps:**
1. ...
2. ...

**Expected Results:**
- ...

---
[repeat for all API test cases]

---

## 4. EVE Device Test Cases
[Include this section only if the EVE flag is set. Otherwise omit entirely.]

### Prerequisites
[SSH access to the device, EVE version, any pre-configuration needed]

---

### EVE-01: <Title>

**Objective:** <one sentence>

**Steps:**
1. SSH into the EVE device: `ssh root@<device-ip>`
2. <exact command>
3. ...

**Expected Results:**
- <exact expected output or state>
- Pubsub path (if applicable): `/run/<agent>/<topic>/*.json`

---
[repeat for all EVE test cases]

---

## 5. Edge Cases and Notes
[table of scenarios not covered by explicit TCs but worth verifying]

---

## 6. References
[links to all source documents provided]
```

### API test case writing principles

**Audience**: A system tester with no access to source code or the running process.

**Strictly forbidden in API test cases:**
- EVE CLI commands or device-side verification of any kind
- Go function or procedure names
- Internal package references (`purus/`, `netinstproc`)
- Source file or line references

**Required format for steps** — every step must be one of:
- An HTTP request: method, endpoint path, and a representative JSON body
- A ZedCloud CLI command with flags and arguments
- An observable system action (e.g., "onboard edge node", "wait for device to check in")

**Required format for expected results:**
- HTTP response status code
- Relevant fields in the response body, or their absence
- Observable ZedCloud state (e.g., "device appears as online in GET /devices/<id>")

**Coverage goal for API test cases:**
1. **Happy path CRUD** — create, read, update, delete
2. **All enum values** — one test per meaningful enum value
3. **All validation rules** — one negative test per rule; bad request → specific error code + message
4. **Sub-configurations** — optional sub-configs tested via their API fields
5. **Cross-resource interactions** — API-observable behavior when related resources change
6. **Edge cases** — empty lists, boundary values, collision checks, reserved names

**What to skip in API test cases:**
- Database migration, column add/drop, schema rollback tests
- Internal infrastructure tests
- Deployment / operator setup tests
- Unit-test-style cases

### EVE test case writing principles

**Audience**: Same system tester, now SSHed into the device.

**Required format for steps:**
- EVE CLI commands: include the full command exactly as it should be run on the device
- Each step describes one observable action on the device

**Required format for expected results:**
- Exact expected command output, or a description of what healthy state looks like
- Pubsub path to inspect if relevant: `/run/<agent>/<topic>/*.json`

**Source of commands:** EVE PR description cross-checked against eve-kb, or eve-kb results
directly. Never invent commands — if the source is unclear or eve-kb returned no result, mark
the step as `[TBD — verify command: <description of what needs to be confirmed>]` and report
the gap to the user explicitly.

---

## Phase 4: Generate the CSV(s)

### API test cases CSV
Save as `<feature-name>-testcases.csv`.

### EVE test cases CSV (only if EVE flag is set)
Save as `<feature-name>-eve-testcases.csv`.

Use Python for both to guarantee correct quoting:

```python
import csv

rows = [
    # (tcid, summary, description, folder, expected_result)
]

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(["TCID", "Test Summary", "Description", "Folder", "Expected Result"])
    for row in rows:
        writer.writerow(row)
```

### Field mapping (same for both CSVs)
| CSV Field | Source |
|-----------|--------|
| TCID | Sequential integer starting at 1. EVE CSV starts at 1 independently. |
| Test Summary | TC title (without the `TC-XX:` or `EVE-XX:` prefix) |
| Description | Objective text + newline + "Steps:" + numbered steps |
| Folder | The value the user provided in Phase 1 |
| Expected Result | Expected results bullet points, joined as sentences |

---

## Delivering the outputs

Once files are saved, provide `computer://` links:

```
Your test plan is ready:

[View test plan .md](computer:///path/to/outputs/feature-testplan.md)
[View API test cases CSV](computer:///path/to/outputs/feature-testcases.csv)
[View EVE test cases CSV](computer:///path/to/outputs/feature-eve-testcases.csv)  <- if generated
```

Give a brief summary: how many API TCs, how many EVE TCs (if any), which areas were covered,
and any gaps where source documents were missing or commands could not be confirmed.
