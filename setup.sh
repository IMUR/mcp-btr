#!/bin/bash
set -e

# MCP-BTR Setup Script
# One-command installation for the Budgeted Tool Router

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  MCP-BTR: Budgeted Tool Router Setup"
echo "=============================================="
echo

# Check prerequisites
check_prerequisites() {
    echo "[1/5] Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo "ERROR: Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi

    echo "  ✓ Docker and Docker Compose found"
}

# Check for .env file
check_env() {
    echo "[2/5] Checking configuration..."

    if [ ! -f .env ]; then
        echo "  Creating .env from template..."
        cp .env.example .env
        echo
        echo "  ⚠️  IMPORTANT: Edit .env with your API keys before continuing!"
        echo "     Required: GITHUB_TOKEN, PERPLEXITY_API_KEY"
        echo
        read -p "  Press Enter after editing .env (or Ctrl+C to abort)..."
    fi

    # Validate required keys
    source .env
    if [ "$GITHUB_TOKEN" = "ghp_your_token_here" ] || [ -z "$GITHUB_TOKEN" ]; then
        echo "  ⚠️  WARNING: GITHUB_TOKEN not configured"
    fi

    echo "  ✓ Configuration checked"
}

# Build containers
build_containers() {
    echo "[3/5] Building containers..."
    docker compose build
    echo "  ✓ Containers built"
}

# Start services
start_services() {
    echo "[4/5] Starting services..."
    docker compose up -d

    # Wait for services to be healthy
    echo "  Waiting for services to start..."
    sleep 5

    # Check if services are running
    if docker compose ps | grep -q "Up"; then
        echo "  ✓ Services started"
    else
        echo "  ⚠️  Some services may have failed to start. Check with: docker compose logs"
    fi
}

# Install AI agents
install_agents() {
    echo "[5/5] Installing AI agents..."

    if [ -d agents ]; then
        bash agents/install.sh
        echo "  ✓ Agents installed"
    else
        echo "  ⚠️  Agents directory not found, skipping"
    fi
}

# Print summary
print_summary() {
    echo
    echo "=============================================="
    echo "  Setup Complete!"
    echo "=============================================="
    echo
    echo "  Services:"
    echo "    BTR Gateway:      http://localhost:${BTR_GATEWAY_PORT:-8090}/mcp"
    echo "    Tool Selector UI: http://localhost:${BTR_UI_PORT:-5010}"
    echo
    echo "  Configure your AI client with:"
    echo '    {"mcpServers": {"btr": {"url": "http://localhost:8090/mcp"}}}'
    echo
    echo "  Commands:"
    echo "    make start   - Start services"
    echo "    make stop    - Stop services"
    echo "    make logs    - View logs"
    echo "    make reset   - Reset to default preset"
    echo
}

# Main
check_prerequisites
check_env
build_containers
start_services
install_agents
print_summary
