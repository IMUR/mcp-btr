#!/bin/bash
# BTR Agent Installer
# Installs AI selection agents to ~/.claude/agents/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing BTR agents..."

# Create agents directory if needed
AGENTS_DIR="$HOME/.claude/agents"
mkdir -p "$AGENTS_DIR"

# Copy agent definitions
cp "$SCRIPT_DIR/btr-tool-selector.md" "$AGENTS_DIR/"
cp "$SCRIPT_DIR/btr-tools-reset.md" "$AGENTS_DIR/"

# Create config file if not exists
CONFIG_FILE="$HOME/.btr.env"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating $CONFIG_FILE from template..."
    cp "$SCRIPT_DIR/.btr.env.example" "$CONFIG_FILE"
    echo "  Edit $CONFIG_FILE to customize BTR host/ports"
else
    echo "  $CONFIG_FILE already exists, skipping"
fi

echo ""
echo "✓ Installed agents:"
echo "  - btr-tool-selector (context-aware tool selection)"
echo "  - btr-tools-reset (reset to clean state)"
echo ""
echo "Configuration: $CONFIG_FILE"
echo ""
echo "Restart Claude Code to load the new agents."
