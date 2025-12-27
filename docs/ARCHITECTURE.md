# MCP-BTR Architecture

Design decisions and system architecture.

## Core Problem

MCP (Model Context Protocol) enables AI clients to use external tools, but the current ecosystem has inefficiencies:

1. **Config sprawl**: Each client configures each server independently
2. **No awareness**: All tools always available regardless of context
3. **Token waste**: LLMs receive 50+ tool descriptions even when only 5 are needed
4. **Manual overhead**: Enabling/disabling requires editing config files

## Solution: Budgeted Tool Router

BTR sits between AI clients and MCP servers, providing:

```
┌─────────────────────────────────────────────────────────────┐
│  AI Clients                                                 │
│  (Cursor, Claude, Gemini)                                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Single HTTP endpoint
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      BTR Gateway                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  - Aggregates multiple MCP servers                     │ │
│  │  - Filters tools based on enabled list                 │ │
│  │  - Routes requests to appropriate server               │ │
│  │  - HTTP SSE transport for client compatibility         │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ GitHub MCP    │    │ Perplexity    │    │ Other MCPs    │
│ (stdio)       │    │ (stdio)       │    │ (stdio)       │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Components

### BTR Gateway (FastAPI)

The core routing service.

**Responsibilities:**
- Discover tools from registered MCP servers
- Maintain enabled/disabled state
- Filter tools in `tools/list` responses
- Route `tools/call` to appropriate server
- Expose management API for UI and agents

**Key Files:**
- `gateway/main.py` - FastAPI application
- `gateway/router.py` - Tool routing logic
- `gateway/config.py` - Configuration and state management

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | MCP JSON-RPC (for AI clients) |
| `/api/tools` | GET | List all tools with enabled state |
| `/api/current` | GET | List enabled tools only |
| `/api/update` | POST | Replace enabled tools |
| `/api/tools/toggle` | POST | Toggle single tool |
| `/api/presets` | GET | List available presets |
| `/api/presets/load` | POST | Load a preset |
| `/health` | GET | Health check |

### Tool Selector UI (Flask)

Web interface for manual tool management.

**Responsibilities:**
- Display all available tools grouped by server
- Show enabled/disabled state
- Allow toggling individual tools
- Manage presets
- Show budget indicators

**Key Files:**
- `ui/app.py` - Flask application (proxies to Gateway)
- `ui/templates/index.html` - Main UI
- `ui/static/app.js` - Frontend logic
- `ui/static/styles.css` - Styling

### AI Selection Agents

Markdown-based agent definitions for Claude Code.

**btr-tool-selector:**
- Analyzes project context (git remote, package files, etc.)
- Determines optimal tool budget
- Executes configuration via API
- Updates project documentation

**btr-tools-reset:**
- Disables all tools
- Updates documentation to clean state

### MCP Servers

Containerized MCP servers registered with BTR.

**Registration:** Each server has a `config.json`:
```json
{
  "name": "github",
  "command": ["docker", "exec", "-i", "github-mcp", "/app/server"],
  "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
}
```

**Discovery:** Gateway sends `tools/list` on startup to discover available tools.

## Data Flow

### Tool Discovery (Startup)

```
1. Gateway starts
2. For each server in servers/:
   a. Read config.json
   b. Execute command with tools/list request
   c. Parse response, index tools
3. Load enabled tools from persistence or default preset
```

### Client Request (tools/list)

```
1. Client POSTs to /mcp with {"method": "tools/list"}
2. Gateway filters all_tools to only enabled tools
3. Returns filtered list with prefixed names
```

### Client Request (tools/call)

```
1. Client POSTs to /mcp with {"method": "tools/call", "params": {...}}
2. Gateway checks if tool is enabled
3. Gateway looks up which server owns the tool
4. Gateway forwards request to server via stdio
5. Gateway returns response to client
```

### Tool Selection Change

```
1. User/agent calls /api/update or /api/tools/toggle
2. Gateway updates enabled_tools set
3. Gateway persists to disk
4. Next tools/list returns updated set
```

## Design Decisions

### Why HTTP Gateway (not stdio)?

- HTTP works with all AI clients
- Easier to deploy (single endpoint)
- No per-client configuration needed
- Supports remote access

### Why Prefix Tool Names?

`github__search_code` instead of just `search_code`:

- Prevents name collisions between servers
- Clear tool origin for users and agents
- Easy filtering by server

### Why Presets?

- Quick switching between contexts
- Sharable configurations
- Baseline for agents to modify

### Why Persist State?

- Survives container restarts
- No need to reconfigure after reboot
- Agents can make persistent changes

## Security Considerations

### API Keys

- Stored in `.env` (never in git)
- Passed to containers via environment
- Never exposed in API responses

### Docker Socket

- Gateway needs docker.sock to communicate with MCP servers
- This grants significant host access
- Consider alternatives for production:
  - TCP connections to MCP servers
  - Dedicated network for MCP communication

### Access Control

- Currently no authentication on BTR APIs
- For multi-user deployments, add auth middleware
- Consider reverse proxy with authentication

## Scaling

### Multiple Clients

- Gateway handles concurrent requests
- Each request routes independently
- No client-specific state (tools are global)

### Multiple BTR Instances

Not currently supported. Considerations:
- Shared persistence (database instead of file)
- Load balancing
- State synchronization

## Future Directions

1. **Tool usage analytics** - Track which tools are actually used
2. **Smart presets** - Learn from usage patterns
3. **Per-client configurations** - Different tool sets for different clients
4. **Tool health monitoring** - Detect and disable failing MCP servers
