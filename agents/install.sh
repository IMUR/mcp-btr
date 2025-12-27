#!/bin/bash
# BTR Agent Installer
# Installs AI selection agents to all detected AI platforms
#
# Usage:
#   ./install.sh                    # Auto-detect platforms
#   ./install.sh --platforms claude_code,cursor
#   ./install.sh --force            # Overwrite existing
#   ./install.sh --legacy           # Use legacy Claude-only install

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for legacy mode flag
if [[ "$1" == "--legacy" ]]; then
    echo "Installing BTR agents (legacy mode)..."

    AGENTS_DIR="$HOME/.claude/agents"
    mkdir -p "$AGENTS_DIR"

    cp "$SCRIPT_DIR/btr-tool-selector.md" "$AGENTS_DIR/"
    cp "$SCRIPT_DIR/btr-tools-reset.md" "$AGENTS_DIR/"

    CONFIG_FILE="$HOME/.btr.env"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Creating $CONFIG_FILE from template..."
        if [ -f "$SCRIPT_DIR/.btr.env.example" ]; then
            cp "$SCRIPT_DIR/.btr.env.example" "$CONFIG_FILE"
        else
            cat > "$CONFIG_FILE" << 'EOF'
# BTR Agent Configuration
BTR_HOST=localhost
BTR_UI_PORT=5010
BTR_GATEWAY_PORT=8090
EOF
        fi
        echo "  Edit $CONFIG_FILE to customize BTR host/ports"
    else
        echo "  $CONFIG_FILE already exists, skipping"
    fi

    echo ""
    echo "Installed agents:"
    echo "  - btr-tool-selector (context-aware tool selection)"
    echo "  - btr-tools-reset (reset to clean state)"
    echo ""
    echo "Configuration: $CONFIG_FILE"
    echo ""
    echo "Restart Claude Code to load the new agents."
    exit 0
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "Python not found. Falling back to legacy install..."
        exec "$0" --legacy
    fi
    PYTHON=python
else
    PYTHON=python3
fi

# Check if installer.py exists
if [ ! -f "$SCRIPT_DIR/installer.py" ]; then
    echo "installer.py not found. Falling back to legacy install..."
    exec "$0" --legacy
fi

# Check for PyYAML
if ! $PYTHON -c "import yaml" 2>/dev/null; then
    echo "PyYAML not installed. Installing..."
    $PYTHON -m pip install --user pyyaml 2>/dev/null || {
        echo "Could not install PyYAML. Falling back to legacy install..."
        exec "$0" --legacy
    }
fi

# Run the Python installer
exec $PYTHON "$SCRIPT_DIR/installer.py" "$@"
