# MCP-BTR: Budgeted Tool Router

> **One HTTP endpoint. Context-aware tool selection. Token-efficient AI.**

MCP-BTR solves the inefficiency of MCP (Model Context Protocol) servers by aggregating them behind a single endpoint and intelligently budgeting which tools are exposed to AI clients.

## The Problem

MCP servers are powerful but inefficient in practice:

- **Config sprawl**: Each AI client must configure each MCP server separately
- **No context awareness**: All tools are always available, regardless of the task
- **Token waste**: LLMs receive descriptions for 50+ irrelevant tools
- **Manual overhead**: Enabling/disabling tools requires editing config files

## The Solution

MCP-BTR is a **budgeted tool router** that:

1. **Aggregates** multiple MCP servers behind one HTTP endpoint
2. **Budgets** tools based on project context (15-30 tools, not 100+)
3. **Routes** only relevant tools to AI clients
4. **Provides** both AI-driven and manual tool selection

```
┌─────────────────────────────────────────────────────────────┐
│  AI Client (Cursor, Claude, Gemini)                         │
│       ↓ Single HTTP endpoint                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  BTR Gateway                                          │  │
│  │  - Aggregates MCP servers                             │  │
│  │  - Serves only enabled tools                          │  │
│  └───────────────────────────────────────────────────────┘  │
│       ↑ Tool selection                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Tool Selector UI  ←→  AI Selection Agents            │  │
│  │  (Manual control)      (Context-aware automation)     │  │
│  └───────────────────────────────────────────────────────┘  │
│       ↓ stdio transport                                     │
│  [GitHub] [Perplexity] [Svelte] [Gitea] [Ark-UI] ...       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Docker Mode (Recommended)

```bash
# Clone and setup
git clone https://github.com/IMUR/mcp-btr
cd mcp-btr
cp .env.example .env
# Edit .env with your API keys

# Start everything
./setup.sh

# Result:
# ✅ BTR Gateway at http://localhost:8090
# ✅ Tool Selector UI at http://localhost:5010
# ✅ AI agents installed to all detected platforms
```

### Standalone Mode (No Docker for MCP servers)

```bash
# Use standalone compose (MCP servers run locally via npx/python)
docker compose -f docker-compose.standalone.yml up -d

# Or set transport mode
export BTR_TRANSPORT_MODE=local
docker compose up -d
```

**Configure your AI client:**

```json
{
  "mcpServers": {
    "btr": {
      "url": "http://localhost:8090/mcp"
    }
  }
}
```

## Features

### Tool Budgeting

Pre-defined presets for common workflows:

| Preset | Tools | Use Case |
|--------|-------|----------|
| `minimal` | 5-10 | Quick tasks, minimal overhead |
| `development` | 15-25 | Full-stack development (default) |
| `research` | 3-5 | Perplexity-focused research |
| `full` | All | When you need everything |

### AI-Driven Selection

The `btr-tool-selector` agent analyzes your project context:

- Detects tech stack from `package.json`, `pyproject.toml`, etc.
- Checks git remote to choose GitHub vs Gitea
- Reads `CLAUDE.md` for explicit tool requirements
- Configures optimal tool budget automatically

**Multi-Platform Support:** Agents work across Claude Code, Cursor, Gemini, and OpenAI.

### Manual Control

The Tool Selector UI provides:

- Visual tool browser organized by server
- One-click preset loading
- Custom tool selection
- Real-time tool count display

## Architecture

```
mcp-btr/
├── gateway/          # BTR Gateway (FastAPI)
│   └── transports/   # Multi-transport support (docker, local, http)
├── ui/               # Tool Selector (Flask)
├── agents/           # AI Selection Agents
│   ├── core/         # Universal agent definitions (YAML)
│   └── platforms/    # Platform-specific generators
├── servers/          # MCP Server definitions
├── presets/          # Tool budget presets
├── cli/              # CLI utilities
└── docs/             # Documentation
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Documentation

- [QUICKSTART.md](docs/QUICKSTART.md) - Detailed setup guide
- [CONFIGURATION.md](docs/CONFIGURATION.md) - All configuration options
- [ADDING_SERVERS.md](docs/ADDING_SERVERS.md) - Adding custom MCP servers
- [AGENTS.md](docs/AGENTS.md) - How AI selection works

## Requirements

- Docker & Docker Compose (or standalone mode with Node.js/Python)
- (Optional) Claude Code, Cursor, Gemini, or OpenAI CLI for AI agents

## License

MIT License - See [LICENSE](LICENSE)
