#!/usr/bin/env bash
# Root setup dispatcher — delegates to the setup.sh of the specified tool folder.
#
# Usage:
#   ./setup.sh <tool>              # e.g. ./setup.sh zcloud-swagger-rag
#   ./setup.sh <tool> [options]    # extra args are forwarded to the tool's setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <tool> [options]"
    echo ""
    echo "Available tools:"
    for d in "$REPO_DIR"/*/; do
        name="$(basename "$d")"
        if [[ -f "$d/setup.sh" ]]; then
            echo "  $name"
        fi
    done
    exit 1
fi

TOOL="$1"
shift

TOOL_DIR="$REPO_DIR/$TOOL"

if [[ ! -d "$TOOL_DIR" ]]; then
    echo "ERROR: folder '$TOOL' not found in $REPO_DIR"
    exit 1
fi

if [[ ! -f "$TOOL_DIR/setup.sh" ]]; then
    echo "ERROR: no setup.sh found in $TOOL_DIR"
    exit 1
fi

echo "==> Running setup for: $TOOL"
echo ""
bash "$TOOL_DIR/setup.sh" "$@"
