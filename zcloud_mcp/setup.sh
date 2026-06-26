#!/usr/bin/env bash
# zcloud-mcp setup: creates venv, installs deps, writes .env, registers MCP server in Claude Code.
# Run once. Re-run safely — it is idempotent.
#
# Usage:
#   ./setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG="$HOME/.mcp.json"
MCP_CONFIG_LEGACY="$HOME/.claude/mcp.json"
SETTINGS_FILE="$HOME/.claude/settings.json"
SERVER_NAME="zcloud_mcp"
SERVER_URL="http://localhost:8000/mcp"

echo ""
echo "=== zcloud-mcp setup ==="
echo ""

# ── Step 1/4: Python virtual environment ──────────────────────────────────────
echo "[1/4] Setting up Python virtual environment..."

if [ ! -d "$REPO_DIR/.venv" ]; then
    python3 -m venv "$REPO_DIR/.venv"
    echo "      Created .venv"
else
    echo "      .venv already exists — skipping"
fi

"$REPO_DIR/.venv/bin/pip" install -q --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -q -e "$REPO_DIR[test]"
echo "      Dependencies installed."

# ── Step 2/4: Environment file ────────────────────────────────────────────────
echo ""
echo "[2/4] Setting up .env file..."

if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    echo "      Created .env from .env.example"
    echo ""
    echo "  ⚠  Edit $REPO_DIR/.env and set:"
    echo "       ZEDCLOUD_BASE_URL=https://zedcontrol.zededa.net"
    echo "       ZEDCLOUD_BEARER_TOKEN=<your token>"
    echo ""
else
    echo "      .env already exists — skipping"
fi

# ── Step 3/4: Server reachability note ────────────────────────────────────────
echo "[3/4] Checking server status..."
if curl -sf "$SERVER_URL/../v1/health" > /dev/null 2>&1; then
    echo "      MCP server is running at $SERVER_URL ✓"
else
    echo "      MCP server is not running yet."
    echo "      Start it with: ./start.sh"
    echo "      (Claude Code will connect automatically once it's running)"
fi

# ── Step 4/4: Register MCP server in Claude Code ──────────────────────────────
echo ""
echo "[4/4] Registering MCP server in Claude Code..."

register_mcp() {
    local config_file="$1"
    local config_dir
    config_dir="$(dirname "$config_file")"

    # Skip if file doesn't exist and parent dir doesn't exist
    if [ ! -f "$config_file" ] && [ ! -d "$config_dir" ]; then
        return
    fi

    mkdir -p "$config_dir"

    # Bootstrap an empty config if the file is missing
    if [ ! -f "$config_file" ]; then
        echo '{"mcpServers":{}}' > "$config_file"
    fi

    # Check if already registered
    if python3 -c "
import json, sys
with open('$config_file') as f:
    cfg = json.load(f)
servers = cfg.get('mcpServers', {})
sys.exit(0 if '$SERVER_NAME' in servers else 1)
" 2>/dev/null; then
        echo "      Already registered in $config_file — skipping"
        return
    fi

    # Add the server entry
    python3 - <<PYEOF
import json

config_file = '$config_file'
with open(config_file) as f:
    cfg = json.load(f)

cfg.setdefault('mcpServers', {})['$SERVER_NAME'] = {
    'type': 'http',
    'url': '$SERVER_URL'
}

with open(config_file, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')

print('      Registered in', config_file)
PYEOF
}

register_mcp "$MCP_CONFIG"
register_mcp "$MCP_CONFIG_LEGACY"

# Enable all project MCP servers in Claude Code settings if the file exists
if [ -f "$SETTINGS_FILE" ]; then
    python3 - <<PYEOF 2>/dev/null || true
import json

settings_file = '$SETTINGS_FILE'
with open(settings_file) as f:
    settings = json.load(f)

if not settings.get('enableAllProjectMcpServers'):
    settings['enableAllProjectMcpServers'] = True
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print('      Enabled enableAllProjectMcpServers in', settings_file)
PYEOF
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env and fill in ZEDCLOUD_BASE_URL and ZEDCLOUD_BEARER_TOKEN"
echo "  2. Start the server:  ./start.sh"
echo "  3. Restart Claude Code to load the MCP server"
echo ""
echo "To verify after restart, ask Claude Code:"
echo "  'check the zcloud mcp server health'"
echo ""
