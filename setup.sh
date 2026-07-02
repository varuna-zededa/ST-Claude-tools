#!/usr/bin/env bash
# Root setup dispatcher — delegates to the setup.sh of the specified tool folder,
# then installs any skills found under skills/.
#
# Usage:
#   ./setup.sh <tool>              # e.g. ./setup.sh zedcloud-kb-rag
#   ./setup.sh <tool> [options]    # extra args are forwarded to the tool's setup.sh
#   ./setup.sh <tool> --no-skills  # run tool setup, skip installing skills from skills/ folder
#   ./setup.sh skills              # install only the skills under skills/, no tool setup
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

install_skills() {
    local skills_dir="$REPO_DIR/skills"
    if [[ -d "$skills_dir" ]]; then
        echo "==> Installing skills from skills/..."
        for skill_dir in "$skills_dir"/*/; do
            skill_name="$(basename "$skill_dir")"
            skill_file="$skill_dir/SKILL.md"
            if [[ -f "$skill_file" ]]; then
                dest="$HOME/.claude/skills/$skill_name"
                mkdir -p "$dest"
                cp "$skill_file" "$dest/SKILL.md"
                echo "      Installed skill: $skill_name → ~/.claude/skills/$skill_name/"
            fi
        done
        echo ""
        echo "Restart Claude Code to activate the installed skills."
    else
        echo "No skills/ directory found — nothing to install."
    fi
}

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <tool> [options]"
    echo "       $0 <tool> --no-skills   # skip installing skills from skills/ folder"
    echo "       $0 skills               # install skills only, no tool setup"
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

# Skills-only mode
if [[ "$TOOL" == "skills" ]]; then
    install_skills
    exit 0
fi

# Parse --no-skills from remaining args; pass everything else to the tool's setup.sh
SKIP_SKILLS=false
TOOL_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--no-skills" ]]; then
        SKIP_SKILLS=true
    else
        TOOL_ARGS+=("$arg")
    fi
done

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
bash "$TOOL_DIR/setup.sh" "${TOOL_ARGS[@]}"

if [[ "$SKIP_SKILLS" == false ]]; then
    echo ""
    install_skills
else
    echo ""
    echo "==> Skipping skills installation (--no-skills)"
fi
