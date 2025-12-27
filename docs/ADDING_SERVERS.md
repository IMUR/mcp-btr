# Adding Custom MCP Servers

Guide to adding your own MCP servers to BTR.

## Overview

BTR discovers MCP servers from the `servers/` directory. Each server has a configuration file that tells BTR how to communicate with it.

## Quick Start

1. Create a server directory:
   ```bash
   mkdir servers/myserver
   ```

2. Create `config.json`:
   ```json
   {
     "name": "myserver",
     "description": "My custom MCP server",
     "command": ["docker", "exec", "-i", "myserver-container", "/app/server"],
     "env": {
       "API_KEY": "${MYSERVER_API_KEY}"
     }
   }
   ```

3. Add the container to `docker-compose.yml`:
   ```yaml
   myserver-mcp:
     image: myserver/mcp:latest
     container_name: myserver-container
     environment:
       - API_KEY=${MYSERVER_API_KEY}
     networks:
       - btr-network
   ```

4. Add `MYSERVER_API_KEY` to `.env`

5. Restart BTR:
   ```bash
   docker compose down && docker compose up -d
   ```

## Configuration Reference

### config.json

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Server identifier (used in tool names) |
| `description` | No | string | Human-readable description |
| `command` | Yes | array | Command to invoke the MCP server |
| `env` | No | object | Environment variables |

### Command Patterns

**Docker exec (recommended for containerized servers):**
```json
{
  "command": ["docker", "exec", "-i", "container-name", "/app/server"]
}
```

**Direct execution (for local binaries):**
```json
{
  "command": ["/path/to/mcp-server", "--stdio"]
}
```

**Python module:**
```json
{
  "command": ["python", "-m", "my_mcp_server"]
}
```

### Environment Variable Substitution

Use `${VAR_NAME}` syntax for environment variables:

```json
{
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "HOST": "${MY_HOST:-https://default.example.com}"
  }
}
```

## Example: Adding Gitea

1. Create `servers/gitea/config.json`:
   ```json
   {
     "name": "gitea",
     "description": "Gitea self-hosted git operations",
     "command": ["docker", "exec", "-i", "gitea-mcp", "/app/gitea-mcp"],
     "env": {
       "GITEA_ACCESS_TOKEN": "${GITEA_TOKEN}",
       "GITEA_HOST": "${GITEA_HOST}"
     }
   }
   ```

2. Add to `docker-compose.yml`:
   ```yaml
   gitea-mcp:
     image: ghcr.io/your-org/gitea-mcp:latest
     container_name: gitea-mcp
     environment:
       - GITEA_ACCESS_TOKEN=${GITEA_TOKEN}
       - GITEA_HOST=${GITEA_HOST}
     networks:
       - btr-network
   ```

3. Add to `.env`:
   ```bash
   GITEA_TOKEN=your_token_here
   GITEA_HOST=https://git.example.com
   ```

## Tool Discovery

BTR discovers tools by sending a `tools/list` request to each server on startup. Tools are automatically prefixed with the server name:

- Server: `gitea`
- Original tool: `create_issue`
- BTR tool name: `gitea__create_issue`

## Troubleshooting

### Server not appearing

1. Check the config.json syntax:
   ```bash
   cat servers/myserver/config.json | jq .
   ```

2. Check gateway logs:
   ```bash
   docker logs btr-gateway
   ```

3. Verify the container is running:
   ```bash
   docker ps | grep myserver
   ```

### Tools not discovered

1. Test the MCP server directly:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
     docker exec -i myserver-container /app/server
   ```

2. Check for errors in the response

### Environment variables not working

1. Verify the variable is set in `.env`
2. Restart the gateway after changes:
   ```bash
   docker compose restart gateway
   ```
