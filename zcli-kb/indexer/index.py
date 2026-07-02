#!/usr/bin/env python3
"""Parse zcli module docstrings and generate commands.json.

Reads every command module under zcli/modules/*.py, extracts the docopt
Usage block and Commands descriptions, and writes a structured commands.json
that the MCP server loads at startup.

No Qdrant or Ollama required — this is a lookup tool, not a RAG pipeline.

Usage:
    python index.py --zcli-path ~/git/zcli
    python index.py --zcli-path ~/git/zcli --output /custom/path/commands.json
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Modules that don't define commands — skip them
SKIP_MODULES = {
    "__init__", "errors", "exceptions", "http_status",
    "output", "utils", "zcli", "config",
}


def _extract_docstring(path: Path) -> str | None:
    """Return the module-level docstring from a .py file, or None."""
    text = path.read_text(encoding="utf-8")
    # Find the first triple-quoted string after any copyright comments
    m = re.search(r'"""(.*?)"""', text, re.DOTALL)
    return m.group(1) if m else None


def _parse_usage_lines(docstring: str) -> list[str]:
    """Extract Usage: lines that start with <app>."""
    lines = []
    in_usage = False
    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("usage:"):
            in_usage = True
            continue
        if in_usage:
            if stripped.startswith("<app>"):
                lines.append(stripped)
            elif stripped and not stripped.startswith("<app>"):
                # A new non-empty non-usage line ends the Usage block
                if not stripped.startswith("#"):
                    in_usage = False
    return lines


def _parse_commands_section(docstring: str) -> dict[str, str]:
    """Return {subcommand: description} from the Commands: section."""
    result = {}
    in_commands = False
    current_sub = None
    desc_lines = []

    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("commands:"):
            in_commands = True
            continue
        if not in_commands:
            continue
        # A new top-level section ends Commands:
        if stripped and not stripped.startswith(" ") and not line.startswith(" ") and stripped.endswith(":"):
            break
        if not stripped:
            continue

        # 1-space indent = subcommand name; 3-space indent = description
        if line.startswith(" ") and not line.startswith("   "):
            # save previous
            if current_sub and desc_lines:
                result[current_sub] = " ".join(desc_lines).strip()
            current_sub = stripped
            desc_lines = []
        elif line.startswith("   ") and current_sub:
            desc_lines.append(stripped)

    if current_sub and desc_lines:
        result[current_sub] = " ".join(desc_lines).strip()

    return result


def _parse_name(docstring: str) -> str:
    """Extract the one-liner from the Name: section."""
    for line in docstring.splitlines():
        if "<app>" in line and " - " in line:
            # e.g. " <app> edge-node - Manage Edge nodes"
            parts = line.split(" - ", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return ""


def _parse_usage_line(raw: str) -> dict | None:
    """
    Parse a single docopt usage line into structured fields.
    raw: "<app> edge-node create <name> --project=<project> [--title=<title>] ..."
    """
    # Remove <app> prefix
    line = re.sub(r"^<app>\s+", "", raw.strip())
    tokens = line.split()
    if len(tokens) < 2:
        return None

    command = tokens[0]
    subcommand = tokens[1]

    # Skip if subcommand is a flag or positional arg
    if subcommand.startswith("-") or subcommand.startswith("<") or subcommand.startswith("("):
        return None

    usage = "zcli " + line

    # Required flags: --flag outside of any [...] or (...)
    # Strip nested brackets iteratively until none remain
    without_optional = line
    while re.search(r"\[[^\[\]]*\]", without_optional):
        without_optional = re.sub(r"\[[^\[\]]*\]", "", without_optional)
    while re.search(r"\([^()]*\)", without_optional):
        without_optional = re.sub(r"\([^()]*\)", "", without_optional)
    required_flags = re.findall(r"--[\w-]+", without_optional)
    # Remove command and subcommand tokens from consideration
    required_flags = [f for f in required_flags]

    # Required positional args: <arg> outside of brackets
    required_args = re.findall(r"<([^>]+)>", without_optional)
    required_args = [a for a in required_args if a not in ("app",)]

    # Optional flags: --flag inside [...]
    optional_sections = re.findall(r"\[([^\[\]]+)\]", line)
    optional_flags = []
    for section in optional_sections:
        optional_flags.extend(re.findall(r"--[\w-]+", section))

    return {
        "command": command,
        "subcommand": subcommand,
        "full_command": f"zcli {command} {subcommand}",
        "usage": usage,
        "required_args": required_args,
        "required_flags": required_flags,
        "optional_flags": list(dict.fromkeys(optional_flags)),  # dedupe, preserve order
        "description": "",        # filled from Commands: section
        "command_description": "",  # filled from Name: section
    }


def parse_module(path: Path) -> list[dict]:
    """Parse a single module file and return a list of subcommand entries."""
    docstring = _extract_docstring(path)
    if not docstring or "Usage:" not in docstring:
        return []

    usage_lines = _parse_usage_lines(docstring)
    if not usage_lines:
        return []

    commands_desc = _parse_commands_section(docstring)
    command_name = _parse_name(docstring)

    entries = []
    for raw in usage_lines:
        entry = _parse_usage_line(raw)
        if entry is None:
            continue
        sub = entry["subcommand"]
        entry["description"] = commands_desc.get(sub, "")
        entry["command_description"] = command_name
        entries.append(entry)

    return entries


def build(zcli_path: Path, output_path: Path) -> None:
    modules_dir = zcli_path / "zcli" / "modules"
    if not modules_dir.exists():
        print(f"ERROR: modules directory not found at {modules_dir}", file=sys.stderr)
        sys.exit(1)

    all_entries = []
    for py_file in sorted(modules_dir.glob("*.py")):
        stem = py_file.stem
        if stem in SKIP_MODULES:
            continue
        entries = parse_module(py_file)
        if entries:
            print(f"  {stem}: {len(entries)} subcommand(s)")
            all_entries.extend(entries)

    # Read zcli version if available
    version = "unknown"
    init_file = zcli_path / "zcli" / "__init__.py"
    if init_file.exists():
        m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_file.read_text())
        if m:
            version = m.group(1)

    output = {
        "version": version,
        "generated": datetime.now(timezone.utc).isoformat(),
        "zcli_path": str(zcli_path),
        "total": len(all_entries),
        "commands": all_entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {len(all_entries)} subcommand entries to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Parse zcli modules into commands.json")
    parser.add_argument("--zcli-path", default=str(Path.home() / "git" / "zcli"),
                        help="Path to zcli repo (default: ~/git/zcli)")
    parser.add_argument("--output", default=None,
                        help="Output path for commands.json (default: <this-dir>/../commands.json)")
    args = parser.parse_args()

    zcli_path = Path(args.zcli_path).expanduser().resolve()
    output_path = Path(args.output) if args.output else Path(__file__).parent.parent / "commands.json"

    print(f"==> Parsing zcli modules from: {zcli_path}")
    build(zcli_path, output_path)
    print("Done.")


if __name__ == "__main__":
    main()
