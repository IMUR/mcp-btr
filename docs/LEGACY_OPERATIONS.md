# Legacy Operations Reference: MCPJungle on CRTR

This document provides working knowledge of the existing MCP tool management implementation running on CRTR. MCP-BTR is intended to formalize and improve upon these patterns.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Clients (Claude Desktop, Claude Code, Cursor, etc.)            │
│  Connect via: npx mcp-remote https://mcp.ism.la/v0/groups/basic/mcp│
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTPS (Caddy reverse proxy)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Caddy Reverse Proxy (mcp.ism.la)                                   │
│  Routes: /api/* → :5010, /v0/* /mcp /health /metrics → :8090       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌─────────────────────┐                    ┌──────────────────────────┐
│  Tool Selector UI   │                    │  MCPJungle Gateway       │
│  Flask :5010        │                    │  Go binary :8090         │
│  - Browse tools     │ docker exec        │  - MCP JSON-RPC endpoint │
│  - Update groups    │─────────────────►  │  - Tool aggregation      │
│  - Manage presets   │                    │  - Session management    │
└─────────────────────┘                    │  - PostgreSQL state      │
                                           └────────────┬─────────────┘
                                                        │ docker exec -i (stdio)
         ┌──────────────┬──────────────┬────────────────┼────────────────┐
         ▼              ▼              ▼                ▼                ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐     ┌──────────┐     ┌──────────┐
   │ github   │  │perplexity│  │ mapbox   │     │elevenlabs│     │  gitea   │
   │   -mcp   │  │   -mcp   │  │   -mcp   │     │   -mcp   │     │   -mcp   │
   └──────────┘  └──────────┘  └──────────┘     └──────────┘     └──────────┘
```

---

## Infrastructure Details

### Server: CRTR (Raspberry Pi 5)
- **Location**: `/media/crtr/fortress/docker/MCPJungle/`
- **Network**: `mcpjungle-network` (Docker bridge)
- **External Domain**: `mcp.ism.la` (HTTPS via Caddy)

### Running Containers

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `mcpjungle-server` | `mcpjungle/mcpjungle:custom-with-docker-cli` | 8090:8080 | MCP Gateway |
| `mcpjungle-tool-selector` | `mcpjungle-tool-selector` | 5010:5000 | Web UI |
| `mcpjungle-db` | `postgres:17` | 5432 | State persistence |
| `github-mcp` | `ghcr.io/github/github-mcp-server:latest` | - | GitHub tools |
| `perplexity-mcp` | `mcp/perplexity-ask:latest` | - | Research tools |
| `mapbox-mcp` | `mcp/mapbox:latest` | - | Geocoding/maps |
| `mapbox-devkit-mcp` | `mcp/mapbox-devkit:latest` | - | Style/token mgmt |
| `elevenlabs-mcp` | `mcp/elevenlabs:latest` | - | TTS/voice |
| `gitea-mcp` | `docker.gitea.com/gitea-mcp-server` | - | Gitea VCS |
| `svelte-mcp` | `oven/bun:1` | - | Svelte docs |
| `ark-ui-mcp` | `oven/bun:1` | - | Ark UI components |

---

## MCP Protocol Implementation

### Session Management

MCPJungle uses HTTP header-based session management:

```bash
# 1. Initialize - returns session ID in header
curl -i -X POST https://mcp.ism.la/v0/groups/basic/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }'

# Response headers include:
# Mcp-Session-Id: mcp-session-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# 2. Subsequent requests MUST include the session header
curl -X POST https://mcp.ism.la/v0/groups/basic/mcp \
  -H 'Content-Type: application/json' \
  -H 'Mcp-Session-Id: mcp-session-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
```

### Initialize Response Format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "prompts": {"listChanged": true},
      "tools": {"listChanged": true}
    },
    "serverInfo": {
      "name": "MCPJungle proxy MCP server for tool group: basic",
      "version": "0.1.0"
    }
  }
}
```

### Tool Naming Convention

Tools are prefixed with their server name using double underscore:

```
{server}__{tool_name}
```

Examples:
- `github__search_code`
- `perplexity__perplexity_ask`
- `gitea__list_repo_issues`
- `elevenlabs__text_to_speech`
- `mapbox__directions_tool`

---

## Endpoints

### MCPJungle Gateway

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | All tools (main gateway) |
| `/v0/groups/{name}/mcp` | POST | Filtered tool group |
| `/v0/servers/{name}/mcp` | POST | Single server's tools |
| `/health` | GET | Health check |
| `/metrics` | GET | OpenTelemetry metrics |

### Tool Selector API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Web UI |
| `/api/tools` | GET | List all tools by server |
| `/api/current` | GET | Current basic group tools |
| `/api/update` | POST | Update basic group |
| `/api/presets` | GET | List saved presets |
| `/api/presets/save` | POST | Save current as preset |
| `/api/presets/load` | POST | Load preset |
| `/api/tools/enable` | POST | Enable single tool |
| `/api/tools/disable` | POST | Disable single tool |
| `/api/tools/toggle` | POST | Toggle tool state |

---

## Configuration Files

### Server Registration: `/configs/*.json`

Each MCP server is registered via a JSON config file:

```json
{
  "name": "github",
  "transport": "stdio",
  "description": "GitHub integration",
  "command": "docker",
  "args": [
    "exec",
    "-i",
    "github-mcp",
    "/server/github-mcp-server",
    "stdio"
  ]
}
```

### Tool Groups: `/groups/*.json`

Groups define subsets of tools exposed via `/v0/groups/{name}/mcp`:

```json
{
  "name": "basic",
  "description": "User-selected basic tools (configured via web UI)",
  "included_tools": [
    "perplexity__perplexity_ask",
    "perplexity__perplexity_reason",
    "perplexity__perplexity_research",
    "github__create_issue",
    "github__list_issues",
    "github__issue_read",
    "github__create_pull_request",
    "github__list_pull_requests",
    "github__pull_request_read",
    "github__get_file_contents",
    "github__create_or_update_file",
    "github__push_files"
  ]
}
```

### Presets: `/groups/presets/*.json`

Saved tool configurations for quick switching:

```json
{
  "name": "development",
  "tools": ["github__search_code", "perplexity__perplexity_ask"]
}
```

---

## Client Configuration

### Claude Code (`~/.claude.json`)

Claude Code only supports stdio transport. Use `mcp-remote` to bridge:

```json
{
  "mcpServers": {
    "ism-basic": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.ism.la/v0/groups/basic/mcp"]
    }
  }
}
```

### Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`)

Same pattern - requires `mcp-remote`:

```json
{
  "mcpServers": {
    "ism-basic": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.ism.la/v0/groups/basic/mcp"]
    }
  }
}
```

### Cursor (`~/.cursor/mcp.json`)

Cursor supports direct HTTP URLs:

```json
{
  "mcpServers": {
    "ism-basic": {
      "url": "https://mcp.ism.la/v0/groups/basic/mcp"
    }
  }
}
```

### Gemini-CLI (`~/.gemini/settings.json`)

Gemini-CLI supports direct HTTP URLs:

```json
{
  "mcpServers": {
    "ism-basic": {
      "url": "https://mcp.ism.la/v0/groups/basic/mcp"
    }
  }
}
```

---

## Operations

### Start All Services

```bash
ssh crtr
cd /media/crtr/fortress/docker/MCPJungle
./start.sh
```

### Deploy (Register Servers + Create Groups)

```bash
./deploy.sh
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker logs mcpjungle-server --tail 50 -f
docker logs mcpjungle-tool-selector --tail 50 -f
```

### List Registered Servers

```bash
docker exec mcpjungle-server /mcpjungle list servers
```

### List All Tools

```bash
docker exec mcpjungle-server /mcpjungle list tools
```

### List Groups

```bash
docker exec mcpjungle-server /mcpjungle list groups
```

### Invoke a Tool Directly

```bash
docker exec mcpjungle-server /mcpjungle invoke github__search_code \
  --input '{"query": "modelcontextprotocol"}'
```

### Update Basic Group via API

```bash
curl -X POST https://mcp.ism.la/api/update \
  -H 'Content-Type: application/json' \
  -d '{"tools": ["github__search_code", "perplexity__perplexity_ask"]}'
```

### Health Check

```bash
curl https://mcp.ism.la/health
# Returns: {"status":"ok"}
```

---

## Secrets Management

All API keys are stored in Infisical and injected at container startup:

| Path | Secret | Used By |
|------|--------|---------|
| `/github` | `GITHUB_PAT` | github-mcp |
| `/mapbox` | `MAPBOX_PUBLIC_API_KEY` | mapbox-mcp |
| `/mapbox` | `MAPBOX_DEV_API_KEY` | mapbox-devkit-mcp |
| `/elevenlabs` | `ELEVENLABS_API_KEY` | elevenlabs-mcp |
| `/perplexity` | `PERPLEXITY_API_KEY` | perplexity-mcp |
| `/gitea` | `GITEA_API_TOKEN` | gitea-mcp |

**No secrets are stored in:**
- Git repository
- Docker Compose files
- Environment files (except temporarily during startup)

---

## Troubleshooting

### "Invalid session ID" Error

The client is not sending the `Mcp-Session-Id` header. This typically means:
1. The client doesn't support HTTP MCP transport natively
2. Solution: Use `mcp-remote` to bridge HTTP to stdio

### Tool Selector Shows No Tools

```bash
# Check MCPJungle is running
docker ps | grep mcpjungle

# Check tool-selector logs
docker logs mcpjungle-tool-selector --tail 20

# Verify servers are registered
docker exec mcpjungle-server /mcpjungle list servers
```

### MCP Server Not Responding

```bash
# Check if container is running
docker ps | grep {server}-mcp

# Test direct communication
docker exec -i github-mcp /server/github-mcp-server stdio <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Claude Desktop/Code Config Error

If you see `"command" required` error:
- Both Claude Desktop and Claude Code require stdio transport
- Cannot use `"url"` directly
- Must use: `"command": "npx", "args": ["mcp-remote", "<url>"]`

---

## Key Differences: MCPJungle vs MCP-BTR

| Feature | MCPJungle (Legacy) | MCP-BTR (This Repo) |
|---------|-------------------|---------------------|
| Language | Go | Python (FastAPI) |
| State Storage | PostgreSQL | JSON file |
| Session Management | `Mcp-Session-Id` header | None (stateless) |
| CLI | `/mcpjungle` binary | None |
| Transport to MCP servers | `docker exec -i` (stdio) | Multi-transport (docker/local/http) |
| Capabilities | `prompts` + `tools` | `tools` only |
| Tool Groups | Multiple named groups | Single enabled list |
| UI | Flask + vanilla JS | Flask + vanilla JS |

---

## Files Reference

### On CRTR

| Path | Purpose |
|------|---------|
| `/media/crtr/fortress/docker/MCPJungle/` | Main project directory |
| `docker-compose.yaml` | Service definitions |
| `configs/*.json` | Server registration configs |
| `groups/*.json` | Tool group definitions |
| `groups/presets/*.json` | Saved presets |
| `tool-selector/app.py` | Flask UI backend |
| `tool-selector/index.html` | Web UI frontend |
| `start.sh` | Startup script |
| `deploy.sh` | Deployment script |

### Documentation on CRTR

| Path | Purpose |
|------|---------|
| `/home/crtr/Projects/crtr-config/docs/mcp/QUICKSTART.md` | Quick start guide |
| `/home/crtr/Projects/crtr-config/docs/mcp/toolchain.md` | Development toolchain |
| `/home/crtr/Projects/crtr-config/docs/mcp/MCP-SERVERS-SUMMARY.md` | Server inventory |
| `/home/crtr/Projects/crtr-config/docs/mcp/HTTPS_ENDPOINTS.md` | Endpoint documentation |
| `/home/crtr/Projects/crtr-config/docs/mcp/TOOL_SELECTOR.md` | UI documentation |

---

## Next Steps for MCP-BTR

Based on the working MCPJungle implementation, MCP-BTR should consider:

1. **Session Management**: Implement `Mcp-Session-Id` header support
2. **Prompts Capability**: Add `prompts.listChanged` to capabilities
3. **Multiple Groups**: Support named tool groups, not just a single enabled list
4. **CLI Tool**: Add a CLI for server/tool/group management
5. **Presets**: Implement preset save/load functionality
6. **Health Checks**: Add per-server health status to `/health` endpoint
