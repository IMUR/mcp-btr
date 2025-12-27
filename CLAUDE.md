# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-BTR (Budgeted Tool Router) aggregates multiple MCP servers behind a single HTTP endpoint and intelligently budgets which tools are exposed to AI clients. It solves the problem of config sprawl and token waste from having too many MCP tools available at once.

## Commands

```bash
# Start all services (Gateway + UI + MCP servers)
make start           # or: docker compose up -d

# Standalone mode (MCP servers run locally, not in Docker)
docker compose -f docker-compose.standalone.yml up -d

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

# Install AI agents to all detected platforms
make install-agents  # or: ./agents/install.sh

# Full cleanup (removes volumes)
make clean

# Check service status
make status

# Check port availability
python cli/port_checker.py
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
  - `gateway/transports/` - Multi-transport support (docker, local, http)
- `ui/` - Flask web interface for manual tool selection
- `agents/` - AI agent definitions for automated tool selection
  - `agents/core/` - Universal agent schemas (YAML)
  - `agents/platforms/` - Platform-specific generators
- `servers/` - MCP server config files (one dir per server with `config.json`)
- `presets/` - JSON tool budget presets (minimal, development, research, full)
- `cli/` - CLI utilities (port checker, etc.)

## Transport Modes

BTR supports multiple transport modes for MCP server communication:

| Mode | Description | Use Case |
|------|-------------|----------|
| `docker` | docker exec into containers | Production (default) |
| `local` | Direct subprocess (npx, python -m) | Development, standalone |
| `http` | HTTP-based MCP servers | Remote servers |
| `auto` | Try docker, then local, then http | Flexible |

Set via `BTR_TRANSPORT_MODE` environment variable.

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

1. Create `servers/{name}/config.json` with multi-transport support:
```json
{
  "name": "myserver",
  "description": "My MCP server",
  "default_transport": "docker",
  "transports": {
    "docker": {
      "container": "myserver-mcp",
      "command": ["/app/server"],
      "env": {"API_KEY": "${MYSERVER_API_KEY}"}
    },
    "local": {
      "command": ["npx", "-y", "@example/mcp-server"],
      "env": {"API_KEY": "${MYSERVER_API_KEY}"}
    }
  }
}
```

2. Add container to `docker-compose.yml` on `btr-network` (for docker transport)
3. Add API key to `.env`
4. Restart: `docker compose down && docker compose up -d`

## Key Files

- `gateway/main.py` - FastAPI app with MCP and management endpoints
- `gateway/router.py` - ToolRouter class: discovers tools, filters by enabled, routes calls
- `gateway/config.py` - Settings and ToolState persistence
- `gateway/transports/` - Transport implementations (docker, stdio, http)
- `gateway/errors.py` - User-friendly error messages with troubleshooting hints
- `ui/app.py` - Flask app that proxies to Gateway API
- `agents/core/*.agent.yaml` - Universal agent definitions
- `agents/generator.py` - Platform-specific agent generator
- `agents/installer.py` - Multi-platform agent installer

## Environment Variables

Required in `.env`:
- `GITHUB_TOKEN` - GitHub PAT
- `PERPLEXITY_API_KEY` - Perplexity API key

Optional:
- `BTR_GATEWAY_PORT` (default: 8090)
- `BTR_UI_PORT` (default: 5010)
- `BTR_DEFAULT_PRESET` (default: development)
- `BTR_TRANSPORT_MODE` (default: auto) - docker, local, http, or auto
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
**Endpoint:** `http://localhost:8090/mcp`
**UI:** `http://localhost:5010`
**Last Updated:** 2025-12-27 UTC

**Currently Enabled:** 12 tools

| Server | Tools | Purpose |
|--------|-------|---------|
| **Perplexity** | `perplexity_ask`, `perplexity_reason`, `perplexity_research` | Research MCP protocol, FastAPI patterns, Docker networking |
| **GitHub** | `create_issue`, `list_issues`, `issue_read`, `create_pull_request`, `list_pull_requests`, `pull_request_read`, `get_file_contents`, `create_or_update_file`, `push_files` | Manage issues, PRs, and files on github.com/IMUR/mcp-btr |

**Why This Configuration:**
- Tech stack: Python (FastAPI/Flask), Docker, MCP protocol
- VCS: GitHub (https://github.com/IMUR/mcp-btr.git)
- Excluded: Gitea (wrong platform), Svelte/Ark-UI (no frontend frameworks), ElevenLabs (no audio), Mapbox (no geo)
- Focus: Infrastructure development with GitHub collaboration and research capabilities
<!-- MCP_TOOLS_END -->
