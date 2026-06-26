#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Copy .env.example to .env if it doesn't exist yet
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[setup] Created .env from .env.example — fill in ZEDCLOUD_BASE_URL and ZEDCLOUD_BEARER_TOKEN"
  exit 1
fi

# Install dependencies if a venv doesn't exist
if [ ! -d .venv ]; then
  echo "[setup] Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[test]"
  echo "[setup] Dependencies installed."
fi

source .venv/bin/activate
echo "[zcloud-mcp] Starting MCP server on http://0.0.0.0:8000/mcp ..."
python mcpserver.py
