#!/usr/bin/env bash
# swagger-rag setup: creates venv, installs deps, writes config.json, installs skill, registers MCP.
# Run once. Re-run safely — it is idempotent.
#
# Usage:
#   ./setup.sh                                          # uses ~/git/zedcloud as swagger path
#   ./setup.sh --swagger-path /custom/path/to/swagger   # specify swagger files location
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG="$HOME/.mcp.json"
MCP_CONFIG_LEGACY="$HOME/.claude/mcp.json"
SETTINGS_FILE="$HOME/.claude/settings.json"
SWAGGER_PATH="$HOME/git/zedcloud"   # default — override with --swagger-path

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --swagger-path) SWAGGER_PATH="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "=== swagger-rag setup ==="
echo "Swagger path: $SWAGGER_PATH"
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
    echo "  WARNING: Qdrant not reachable at http://localhost:6333"
    echo "  Start Qdrant before running the indexer:"
    echo "  (Docker: docker run -p 6333:6333 qdrant/qdrant)"
else
    echo "      Qdrant OK"
fi

if ! pgrep -x ollama > /dev/null 2>&1; then
    echo "  WARNING: Ollama not running. Start it with: ollama serve"
elif ! ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "  Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
    echo "      OK"
else
    echo "      Ollama + nomic-embed-text OK"
fi

# 3. Write config.json --------------------------------------------------------
echo "[3/5] Writing config.json..."
cat > "$REPO_DIR/config.json" <<EOF
{
  "swagger_path": "$SWAGGER_PATH",
  "qdrant_url": "http://localhost:6333"
}
EOF
echo "      Written: $REPO_DIR/config.json"

# 4. Install skill -------------------------------------------------------------
echo "[4/5] Installing zcloud_swagger_mcp skill..."
mkdir -p "$HOME/.claude/skills/zcloud_swagger_mcp"
cp "$REPO_DIR/skills/zcloud_swagger_mcp/SKILL.md" "$HOME/.claude/skills/zcloud_swagger_mcp/SKILL.md"
echo "      Installed to ~/.claude/skills/zcloud_swagger_mcp/"

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
        cfg.setdefault("mcpServers", {})["zcloud_swagger_mcp"] = server_entry
        with open(mcp_path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"      Registered zcloud_swagger_mcp in {mcp_path}")
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
echo "Next step — ingest your swagger files:"
echo ""
echo "  source $REPO_DIR/.venv/bin/activate"
echo "  python $REPO_DIR/indexer/index.py ~/git/zedcloud/zservices/swagger/*.swagger.json"
echo ""
echo "To re-ingest (wipes and rebuilds the collection):"
echo "  python $REPO_DIR/indexer/index.py --reset /path/to/*.swagger.json"
echo ""
echo "Restart Claude Code to pick up the new MCP server and skill."
