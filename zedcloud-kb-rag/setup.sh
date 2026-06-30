#!/usr/bin/env bash
# zedcloud-kb setup: creates venv, installs deps, writes config.json, installs skill, registers MCP.
# Run once. Re-run safely — it is idempotent.
#
# Usage:
#   ./setup.sh                                   # uses ~/git/zedcloud as ZedCloud path
#   ./setup.sh --zcloud-path /custom/path        # specify ZedCloud repo location
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG="$HOME/.mcp.json"
MCP_CONFIG_LEGACY="$HOME/.claude/mcp.json"
SETTINGS_FILE="$HOME/.claude/settings.json"
ZCLOUD_PATH="$HOME/git/zedcloud"   # default

while [[ $# -gt 0 ]]; do
    case "$1" in
        --zcloud-path) ZCLOUD_PATH="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "=== zedcloud-kb setup ==="
echo "ZedCloud path: $ZCLOUD_PATH"
echo ""

# 1. Python venv ---------------------------------------------------------------
echo "[1/5] Setting up Python virtual environment..."
python3 -m venv "$REPO_DIR/.venv"
# shellcheck disable=SC1091
source "$REPO_DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$REPO_DIR/requirements.txt"
echo "      OK"

# 2. Check required services ---------------------------------------------------
echo "[2/5] Checking Qdrant and Ollama..."
if ! curl -sf "http://localhost:6333/healthz" > /dev/null 2>&1; then
    echo ""
    echo "  ERROR: Qdrant not reachable at http://localhost:6333"
    echo "  Start Qdrant first, then re-run this script."
    echo "  (If using Docker: docker run -p 6333:6333 qdrant/qdrant)"
    exit 1
fi
if ! ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "  Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
fi
echo "      OK"

# 3. Write config.json --------------------------------------------------------
echo "[3/5] Writing config.json..."
cat > "$REPO_DIR/config.json" <<EOF
{
  "zcloud_path": "$ZCLOUD_PATH",
  "qdrant_url": "http://localhost:6333",
  "github_branch": "main"
}
EOF
echo "      Written: $REPO_DIR/config.json"

# 4. Install skill -------------------------------------------------------------
echo "[4/5] Installing zcloud-kb skill..."
mkdir -p "$HOME/.claude/skills/zcloud-kb"
cp "$REPO_DIR/skills/zcloud-kb/SKILL.md" "$HOME/.claude/skills/zcloud-kb/SKILL.md"
echo "      Installed to ~/.claude/skills/zcloud-kb/"

# 5. Register MCP server -------------------------------------------------------
echo "[5/5] Registering MCP server in ~/.mcp.json and ~/.claude/mcp.json..."
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
        cfg.setdefault("mcpServers", {})["zcloud-kb"] = server_entry
        with open(mcp_path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"      Registered zcloud-kb in {mcp_path}")
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
echo "Next step — run the indexer (takes ~10-20 min first time):"
echo ""
echo "  source $REPO_DIR/.venv/bin/activate"
echo "  python $REPO_DIR/indexer/index.py --zcloud-path $ZCLOUD_PATH"
echo ""
echo "Options:"
echo "  --reset          Wipe and re-index from scratch"
echo "  --skip-swagger   Skip swagger endpoint indexing (faster)"
echo "  --skip-source    Skip Go source indexing"
echo ""
echo "To index directly from GitHub (no local clone needed):"
echo "  export GITHUB_TOKEN=<your-token>"
echo "  python $REPO_DIR/indexer/index.py --source github"
echo "  python $REPO_DIR/indexer/index.py --source github --branch main --reset"
echo ""
echo "Restart Claude Code to pick up the new MCP server and skill."
