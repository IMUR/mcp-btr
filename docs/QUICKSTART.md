# MCP-BTR Quick Start Guide

Get MCP-BTR running in 5 minutes.

## Prerequisites

- Docker & Docker Compose
- API keys for the MCP servers you want to use

## Step 1: Clone & Configure

```bash
git clone https://github.com/IMUR/mcp-btr
cd mcp-btr

# Create your config
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required
GITHUB_TOKEN=ghp_your_github_token_here
PERPLEXITY_API_KEY=pplx-your_key_here
```

## Step 2: Start Services

```bash
./setup.sh
# or manually:
docker compose up -d
```

## Step 3: Configure Your AI Client

Add BTR as your MCP server.

**For Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "btr": {
      "url": "http://localhost:8090/mcp"
    }
  }
}
```

**For Claude Code** (`~/.claude/settings.local.json`):
```json
{
  "mcpServers": {
    "btr": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8090/mcp"]
    }
  }
}
```

## Step 4: Select Tools

Open the Tool Selector UI: http://localhost:5010

- Browse available tools by server
- Select the tools you need
- Or load a preset (minimal, development, research, full)

## Step 5: (Optional) Install AI Agents

For automatic context-aware tool selection:

```bash
./agents/install.sh
```

This installs:
- `btr-tool-selector` - Analyzes your project and configures optimal tools
- `btr-tools-reset` - Resets to clean state

## Verify It's Working

Check the gateway health:
```bash
curl http://localhost:8090/health
```

List enabled tools:
```bash
curl http://localhost:8090/api/current
```

## Common Operations

```bash
# Start services
make start

# Stop services
make stop

# View logs
make logs

# Reset to default preset
make reset

# Check status
make status
```

## Next Steps

- [CONFIGURATION.md](CONFIGURATION.md) - All configuration options
- [ADDING_SERVERS.md](ADDING_SERVERS.md) - Add custom MCP servers
- [AGENTS.md](AGENTS.md) - Using AI selection agents
