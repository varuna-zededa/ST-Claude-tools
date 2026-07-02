#!/usr/bin/env python3
"""MCP server exposing zcli command search to Claude Code.

Two tools:
  kb_info        — version, total command count, source path, generated timestamp
  search_zcli_kb — search for zcli commands by feature, flag, or subcommand name

No Qdrant or Ollama required. Loads commands.json into memory at startup
and does keyword scoring at query time.
"""

import json
import re
from pathlib import Path

from fastmcp import FastMCP

_CONFIG_FILE = Path(__file__).parent.parent / "config.json"
_COMMANDS_FILE = Path(__file__).parent.parent / "commands.json"


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}


_CFG = _load_config()
ZCLI_PATH = _CFG.get("zcli_path", str(Path.home() / "git" / "zcli"))

mcp = FastMCP("zcli-kb")

_db: dict = {}


def _load_db() -> dict:
    global _db
    if not _db:
        if not _COMMANDS_FILE.exists():
            return {}
        _db = json.loads(_COMMANDS_FILE.read_text())
    return _db


def _score(entry: dict, terms: list[str]) -> int:
    """Score an entry against a list of query terms. Higher = better match."""
    score = 0
    command = entry["command"].lower()
    subcommand = entry["subcommand"].lower()
    description = entry["description"].lower()
    command_desc = entry["command_description"].lower()
    usage = entry["usage"].lower()
    all_flags = " ".join(entry["required_flags"] + entry["optional_flags"]).lower()

    for term in terms:
        t = term.lower().strip("-")
        if t in command:
            score += 4
        if t == subcommand:
            score += 4
        elif t in subcommand:
            score += 2
        if t in description:
            score += 2
        if t in command_desc:
            score += 1
        if t in usage:
            score += 1
        if t in all_flags:
            score += 2

    return score


def _format_entry(entry: dict, rank: int) -> str:
    lines = [
        f"### {rank}. `{entry['full_command']}`",
        f"**{entry['command_description']}** — {entry['description']}" if entry["description"] else f"**{entry['command_description']}**",
        "",
        f"```",
        entry["usage"],
        f"```",
    ]
    if entry["required_args"]:
        lines.append(f"**Required args:** {', '.join(f'<{a}>' for a in entry['required_args'])}")
    if entry["required_flags"]:
        lines.append(f"**Required flags:** {', '.join(entry['required_flags'])}")
    if entry["optional_flags"]:
        lines.append(f"**Optional flags:** {', '.join(entry['optional_flags'])}")
    return "\n".join(lines)


@mcp.tool()
def kb_info() -> str:
    """Show zcli-kb status: version, total commands indexed, and when it was generated."""
    db = _load_db()
    if not db:
        return "commands.json not found. Run the indexer: python indexer/index.py --zcli-path ~/git/zcli"
    return (
        f"zcli-kb\n"
        f"  zcli version : {db.get('version', 'unknown')}\n"
        f"  commands     : {db.get('total', 0)} subcommands across all modules\n"
        f"  generated    : {db.get('generated', 'unknown')}\n"
        f"  source       : {db.get('zcli_path', 'unknown')}\n"
    )


@mcp.tool()
def search_zcli_kb(
    query: str,
    command: str = "",
    top_k: int = 5,
) -> str:
    """Search zcli commands by feature name, flag, or action.

    Args:
        query:   Natural language or keyword query, e.g. "create edge node",
                 "configure wifi", "list projects", "--model flag"
        command: Optional — filter to a specific command group, e.g. "edge-node",
                 "network", "project"
        top_k:   Max results to return (default 5)
    """
    db = _load_db()
    if not db:
        return "commands.json not found. Run: python indexer/index.py --zcli-path ~/git/zcli"

    entries = db.get("commands", [])

    # Filter by command group if specified
    if command:
        entries = [e for e in entries if command.lower() in e["command"].lower()]

    # Score all entries
    terms = re.split(r"[\s,]+", query.strip())
    terms = [t for t in terms if t]

    scored = [(e, _score(e, terms)) for e in entries]
    scored = [(e, s) for e, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]

    if not top:
        return (
            f"No commands matched '{query}'.\n"
            f"Try broader terms or check `kb_info()` to confirm the index is loaded.\n"
            f"Available command groups: {', '.join(sorted({e['command'] for e in db['commands']}))}"
        )

    header = f"**{len(top)} result(s) for '{query}'**\n"
    if command:
        header += f"*(filtered to `{command}` commands)*\n"
    header += "\n---\n"

    results = "\n\n---\n\n".join(_format_entry(e, i + 1) for i, (e, _) in enumerate(top))
    return header + results


if __name__ == "__main__":
    mcp.run()
