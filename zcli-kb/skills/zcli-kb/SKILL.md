---
name: zcli-kb
description: >
  Search zcli commands for configuring ZedCloud features. Use when the user explicitly
  mentions zcli — e.g. "what zcli command", "how do I configure X in zcli",
  "zcli flag for", "what flags does zcli", "how to set up X with zcli", "zcli create",
  "zcli update", "zcli show", or "using zcli" followed by a resource name like
  "edge node", "network instance", "project", "image", "cluster".
  Do NOT trigger on general ZedCloud questions without an explicit zcli mention.
  Returns the exact command syntax with required and optional flags.
---

# zcli-kb — ZedCloud CLI Command Search

You are helping the user find the right `zcli` command and its exact syntax.

## When this skill is active

The user **explicitly mentions zcli** and wants to:
- Configure, create, update, delete, or show a ZedCloud resource via zcli
- Know what flags a zcli command requires or supports
- Find which zcli command handles a given feature or field

Do NOT activate for general ZedCloud API questions — those go to `zcloud-kb`.

## How to use the MCP tools

**Step 1 — Check availability**

Call `kb_info()` first. If it returns an error (commands.json missing), tell the user:
> The zcli-kb index is not built. Run:
> ```bash
> cd ~/git/ST-Claude-tools
> ./update-index.sh zcli-kb --zcli-path ~/git/zcli
> ```
> Then restart Claude Code.

**Step 2 — Search**

Call `search_zcli_kb(query=<user's intent>)`.

- Use the feature or resource name as the query: `"create edge node"`, `"configure wifi network"`, `"update project"`
- If the user mentions a specific command group, pass it as `command=`: `command="edge-node"`
- If results are too broad, narrow with a more specific query or add `command=`
- If no results match, try synonyms: "network" → "network-instance", "device" → "edge-node"

**Step 3 — Present the result**

Return the command with:
1. The full usage line (exact syntax)
2. Required args and flags called out clearly
3. Optional flags listed so the user knows what's available
4. A one-line description of what the command does

If multiple commands match (e.g. create vs update), present both and ask which the user needs.

## What NOT to do

- Do not invent flags or syntax not in the search result
- Do not reference ZedCloud API endpoints — this skill is zcli only
- If the user needs API-level detail, direct them to `search_zcloud_kb` instead
