# MCP-BTR Configuration

Complete reference for all configuration options.

## Environment Variables

All configuration is done via environment variables in `.env`.

### Required

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `PERPLEXITY_API_KEY` | Perplexity API key |

### Service Ports

| Variable | Default | Description |
|----------|---------|-------------|
| `BTR_GATEWAY_PORT` | 8090 | Gateway HTTP port |
| `BTR_UI_PORT` | 5010 | Tool Selector UI port |

### Defaults

| Variable | Default | Description |
|----------|---------|-------------|
| `BTR_DEFAULT_PRESET` | development | Preset loaded on startup |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Additional MCP Servers

| Variable | Description |
|----------|-------------|
| `GITEA_TOKEN` | Gitea API token |
| `GITEA_HOST` | Gitea instance URL |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS API key |
| `MAPBOX_TOKEN` | Mapbox access token |

## Agent Configuration

Agents use `~/.btr.env` for configuration:

```bash
# BTR host (localhost or remote hostname)
BTR_HOST=localhost

# Ports
BTR_UI_PORT=5010
BTR_GATEWAY_PORT=8090
```

## Presets

Presets are JSON files in `presets/`:

```json
{
  "name": "my-preset",
  "description": "My custom tool selection",
  "tools": [
    "github__search_code",
    "perplexity__perplexity_ask"
  ]
}
```

### Available Presets

| Preset | Tools | Use Case |
|--------|-------|----------|
| `minimal` | 3 | Quick tasks, minimal overhead |
| `development` | 15 | Standard development work |
| `research` | 3 | Perplexity-focused research |
| `full` | 22+ | All available tools |

## Tool Naming Convention

Tools use the pattern: `{server}__{tool_name}`

Examples:
- `github__search_code`
- `perplexity__perplexity_ask`
- `gitea__create_issue`

## Network Configuration

### Docker Network

All services run on `btr-network` (bridge driver).

### Exposing to LAN

To access from other machines, bind to `0.0.0.0` (default) and ensure firewall allows access to:
- Gateway: `BTR_GATEWAY_PORT` (default 8090)
- UI: `BTR_UI_PORT` (default 5010)

### Remote Access for Agents

For agents running on a different machine:

1. Set `BTR_HOST` in `~/.btr.env` to the BTR server's hostname/IP
2. Ensure network connectivity to the configured ports

## Health Checks

Both services expose health endpoints:

```bash
# Gateway
curl http://localhost:8090/health

# UI
curl http://localhost:5010/health
```

## Persistence

Tool selections are persisted in the `btr-data` Docker volume:
- Location: `/app/data/enabled_tools.json` (inside container)
- Survives container restarts
- Reset with `make clean` (removes volume)
