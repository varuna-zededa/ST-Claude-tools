#!/usr/bin/env bash
# zcli-kb setup: creates venv, parses zcli modules into commands.json,
# installs the Claude Code skill, and registers the MCP server.
# Run once. Re-run safely — it is idempotent.
#
# Usage:
#   ./setup.sh                             # uses ~/git/zcli as zcli path
#   ./setup.sh --zcli-path /custom/path    # specify zcli repo location
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG="$HOME/.mcp.json"
MCP_CONFIG_LEGACY="$HOME/.claude/mcp.json"
SETTINGS_FILE="$HOME/.claude/settings.json"
ZCLI_PATH="$HOME/git/zcli"   # default

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zcli-path) ZCLI_PATH="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "=== zcli-kb setup ==="
echo "zcli path: $ZCLI_PATH"
echo ""

# 1. Python venv ---------------------------------------------------------------
echo "[1/4] Setting up Python virtual environment..."
python3 -m venv "$REPO_DIR/.venv"
# shellcheck disable=SC1091
source "$REPO_DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$REPO_DIR/requirements.txt"
echo "      OK"

# 2. Write config.json ---------------------------------------------------------
echo "[2/4] Writing config.json..."
cat > "$REPO_DIR/config.json" <<EOF
{
  "zcli_path": "$ZCLI_PATH"
}
EOF
echo "      Written: $REPO_DIR/config.json"

# 3. Parse zcli modules → commands.json ----------------------------------------
echo "[3/4] Parsing zcli modules..."
python "$REPO_DIR/indexer/index.py" --zcli-path "$ZCLI_PATH"
echo "      OK"

# 4. Install skill -------------------------------------------------------------
echo "[4/4] Installing zcli-kb skill..."
mkdir -p "$HOME/.claude/skills/zcli-kb"
cp "$REPO_DIR/skills/zcli-kb/SKILL.md" "$HOME/.claude/skills/zcli-kb/SKILL.md"
echo "      Installed to ~/.claude/skills/zcli-kb/"

# 5. Register MCP server -------------------------------------------------------
echo "[5/4] Registering MCP server in ~/.mcp.json..."
VENV_PYTHON="$REPO_DIR/.venv/bin/python"
MCP_SCRIPT="$REPO_DIR/mcp_server/server.py"

[ -f "$MCP_CONFIG" ]        || echo '{"mcpServers":{}}' > "$MCP_CONFIG"
[ -f "$MCP_CONFIG_LEGACY" ] || echo '{"mcpServers":{}}' > "$MCP_CONFIG_LEGACY"

python3 - <<PYEOF
import json, sys

server_entry = {
    "command": "$VENV_PYTHON",
    "args": ["$MCP_SCRIPT"]
}

for mcp_path in ["$MCP_CONFIG", "$MCP_CONFIG_LEGACY"]:
    try:
        with open(mcp_path) as f:
            cfg = json.load(f)
        cfg.setdefault("mcpServers", {})["zcli-kb"] = server_entry
        with open(mcp_path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"      Registered zcli-kb in {mcp_path}")
    except Exception as e:
        print(f"      WARNING: could not update {mcp_path}: {e}", file=sys.stderr)

try:
    with open("$SETTINGS_FILE") as f:
        settings = json.load(f)
    if not settings.get("enableAllProjectMcpServers"):
        settings["enableAllProjectMcpServers"] = True
        with open("$SETTINGS_FILE", "w") as f:
            json.dump(settings, f, indent=2)
        print(f"      Set enableAllProjectMcpServers=true in $SETTINGS_FILE")
except Exception as e:
    print(f"      WARNING: could not update $SETTINGS_FILE: {e}", file=sys.stderr)
PYEOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Restart Claude Code to activate the zcli-kb MCP server and skill."
echo ""
echo "To refresh the command index after zcli updates:"
echo "  cd $(dirname "$REPO_DIR") && ./update-index.sh zcli-kb --zcli-path $ZCLI_PATH"
