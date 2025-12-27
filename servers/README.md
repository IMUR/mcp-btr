# MCP Server Definitions

This directory contains the configuration for each MCP server that BTR can aggregate.

## Structure

Each server has its own subdirectory with:
- `config.json` - Server configuration
- `Dockerfile` (optional) - If the server needs a custom container

## Adding a New Server

1. Create a new directory: `servers/myserver/`
2. Create `config.json`:

```json
{
  "name": "myserver",
  "description": "Description of what this server provides",
  "command": ["docker", "exec", "-i", "myserver-mcp", "/app/server"],
  "env": {
    "API_KEY": "${MYSERVER_API_KEY}"
  }
}
```

3. If the server needs a container, create a `Dockerfile` and add it to `docker-compose.yml`

4. Restart BTR to discover the new tools

## Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Server identifier (used in tool names) |
| `description` | No | Human-readable description |
| `command` | Yes | Command to start the MCP server (stdio transport) |
| `env` | No | Environment variables to pass (supports `${VAR}` substitution) |

## Tool Naming Convention

Tools are exposed with the pattern: `{server}__{tool_name}`

For example, a server named `github` with a tool called `search_code` becomes `github__search_code`.

This allows:
- Clear identification of tool origin
- Easy filtering by server
- No name collisions between servers

## Available Servers

| Server | Tools | Description |
|--------|-------|-------------|
| github | ~48 | GitHub repository operations |
| perplexity | 3 | AI-powered web search |

(Add your servers here)
