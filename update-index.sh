#!/usr/bin/env bash
# Update the knowledge base index for a given tool. Activates the tool's venv
# and forwards all remaining arguments to the tool's indexer/index.py.
# Run this whenever the source repo has changed and you want to refresh the index.
#
# Usage:
#   ./update-index.sh <tool> [indexer options]
#
# Examples:
#   ./update-index.sh zedcloud-kb-rag
#   ./update-index.sh zedcloud-kb-rag --zcloud-path /custom/path
#   ./update-index.sh zedcloud-kb-rag --source github --branch main --reset
#   ./update-index.sh zedcloud-kb-rag --skip-source
#
#   ./update-index.sh eve-kb-rag
#   ./update-index.sh eve-kb-rag --eve-path /custom/path/eve
#   ./update-index.sh eve-kb-rag --source github --branch eve-9.13 --reset
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo "Usage: $0 <tool> [indexer options]"
    echo ""
    echo "Available tools:"
    for d in "$REPO_DIR"/*/; do
        name="$(basename "$d")"
        if [[ -f "$d/indexer/index.py" ]]; then
            echo "  $name"
        fi
    done
    echo ""
    echo "zedcloud-kb-rag options:"
    echo "  --zcloud-path <path>   Local ZedCloud repo path (default: ~/git/zedcloud)"
    echo "  --source github        Index from GitHub instead of local clone"
    echo "  --branch <name>        GitHub branch to index (default: main)"
    echo "  --reset                Wipe and rebuild the collection from scratch"
    echo "  --skip-source          Skip Go source indexing (largest/slowest; use when only API specs changed)"
    echo ""
    echo "eve-kb-rag options:"
    echo "  --eve-path <path>      Local EVE repo path (default: ~/git/eve)"
    echo "  --source github        Index from GitHub instead of local clone"
    echo "  --branch <name>        GitHub branch to index (default: master)"
    echo "  --reset                Wipe and rebuild the collection from scratch"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

TOOL="$1"
shift

TOOL_DIR="$REPO_DIR/$TOOL"
VENV="$TOOL_DIR/.venv"
INDEXER="$TOOL_DIR/indexer/index.py"

if [[ ! -d "$TOOL_DIR" ]]; then
    echo "ERROR: folder '$TOOL' not found in $REPO_DIR"
    exit 1
fi

if [[ ! -f "$INDEXER" ]]; then
    echo "ERROR: no indexer found at $INDEXER"
    exit 1
fi

if [[ ! -d "$VENV" ]]; then
    echo "ERROR: venv not found at $VENV"
    echo "Run './setup.sh $TOOL' first to create the venv."
    exit 1
fi

echo "==> Updating index for: $TOOL"
echo ""

# shellcheck disable=SC1091
source "$VENV/bin/activate"
python "$INDEXER" "$@"
