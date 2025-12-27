# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-BTR (Budgeted Tool Router) aggregates multiple MCP servers behind a single HTTP endpoint and intelligently budgets which tools are exposed to AI clients. It solves the problem of config sprawl and token waste from having too many MCP tools available at once.

## Commands

```bash
# Start all services (Gateway + UI + MCP servers)
make start           # or: docker compose up -d

# Stop services
make stop            # or: docker compose down

# View logs
make logs            # All services
make logs-gateway    # Gateway only
make logs-ui         # UI only

# Rebuild containers
make build           # or: docker compose build

# Reset to default preset
make reset

# Install AI agents to ~/.claude/agents/
make install-agents  # or: ./agents/install.sh

# Full cleanup (removes volumes)
make clean

# Check service status
make status
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AI Client (via HTTP POST to /mcp)                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│  BTR Gateway (FastAPI) :8090                                │
│  - Aggregates MCP servers via stdio                         │
│  - Filters tools based on enabled list                      │
│  - Routes tool calls to appropriate server                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ GitHub MCP    │    │ Perplexity    │    │ Other MCPs    │
│ (container)   │    │ (container)   │    │ (container)   │
└───────────────┘    └───────────────┘    └───────────────┘
```

**Key Components:**
- `gateway/` - FastAPI service that handles MCP protocol and tool routing
- `ui/` - Flask web interface for manual tool selection
- `agents/` - AI agent definitions for automated tool selection
- `servers/` - MCP server config files (one dir per server with `config.json`)
- `presets/` - JSON tool budget presets (minimal, development, research, full)

## Tool Naming Convention

Tools are prefixed with server name using double underscore: `{server}__{tool_name}`

Examples:
- `github__search_code`
- `perplexity__perplexity_ask`
- `gitea__create_issue`

## Gateway API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | MCP JSON-RPC (initialize, tools/list, tools/call) |
| `/api/tools` | GET | All tools with enabled state, grouped by server |
| `/api/current` | GET | Currently enabled tools only |
| `/api/update` | POST | Replace all enabled tools `{"tools": [...]}` |
| `/api/tools/enable` | POST | Enable single tool `{"tool": "name"}` |
| `/api/tools/disable` | POST | Disable single tool |
| `/api/tools/toggle` | POST | Toggle single tool |
| `/api/presets` | GET | List available presets |
| `/api/presets/load` | POST | Load a preset `{"name": "development"}` |
| `/health` | GET | Health check with server/tool counts |

## Adding New MCP Servers

1. Create `servers/{name}/config.json`:
```json
{
  "name": "myserver",
  "description": "My MCP server",
  "command": ["docker", "exec", "-i", "myserver-container", "/app/server"],
  "env": {
    "API_KEY": "${MYSERVER_API_KEY}"
  }
}
```

2. Add container to `docker-compose.yml` on `btr-network`
3. Add API key to `.env`
4. Restart: `docker compose down && docker compose up -d`

## Key Files

- `gateway/main.py` - FastAPI app with MCP and management endpoints
- `gateway/router.py` - ToolRouter class: discovers tools, filters by enabled, routes calls
- `gateway/config.py` - Settings and ToolState persistence
- `ui/app.py` - Flask app that proxies to Gateway API

## Environment Variables

Required in `.env`:
- `GITHUB_TOKEN` - GitHub PAT
- `PERPLEXITY_API_KEY` - Perplexity API key

Optional:
- `BTR_GATEWAY_PORT` (default: 8090)
- `BTR_UI_PORT` (default: 5010)
- `BTR_DEFAULT_PRESET` (default: development)
- `LOG_LEVEL` (default: INFO)

## Testing APIs

```bash
# Check gateway health
curl http://localhost:8090/health

# List enabled tools
curl http://localhost:8090/api/current

# Load a preset
curl -X POST http://localhost:8090/api/presets/load \
  -H 'Content-Type: application/json' \
  -d '{"name": "minimal"}'

# Test MCP protocol
curl -X POST http://localhost:8090/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'
```

## Persistence

Tool state is stored in Docker volume `btr-data` at `/app/data/enabled_tools.json`. Survives restarts; cleared with `make clean`.

## MCP Tools (MCPJungle)

<!-- MCP_TOOLS_START -->
**Endpoint:** `http://localhost:8090/v0/groups/basic/mcp`
**UI:** `http://localhost:5010`
**Last Updated:** 2025-12-27 10:35 UTC

**Currently Enabled:** 3 tools

| Server | Tools | Purpose |
|--------|-------|---------|
| **Perplexity** | `perplexity_ask`, `perplexity_reason`, `perplexity_research` | Research MCP protocol, FastAPI patterns, Docker networking |

**Why This Configuration:**
- Tech stack: Python (FastAPI/Flask), Docker
- VCS: None (no git remote configured)
- Excluded: GitHub/Gitea (no VCS), Svelte/Ark-UI (no frontend), ElevenLabs (no audio), Mapbox (no geo)
- This is the BTR infrastructure project itself - minimal research tools only
<!-- MCP_TOOLS_END -->
