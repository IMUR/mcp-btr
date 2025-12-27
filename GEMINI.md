# MCP-BTR: Budgeted Tool Router

**MCP-BTR** is a "Budgeted Tool Router" for the Model Context Protocol (MCP). It aggregates multiple MCP servers behind a single HTTP endpoint and intelligently budgets which tools are exposed to AI clients. This solves the problem of "config sprawl" and "token waste" by allowing context-aware tool selection.

## Project Overview

*   **Goal:** Efficiently manage and route tools from multiple MCP servers to AI clients through a unified gateway.
*   **Architecture:**
    *   **Gateway (`gateway/`):** FastAPI service that handles MCP protocol, tool discovery, and routing.
    *   **UI (`ui/`):** Flask web interface for manual tool selection and visualization.
    *   **MCP Servers (`servers/`):** Containerized tool providers (e.g., GitHub, Perplexity).
    *   **Agents (`agents/`):** Definitions for AI agents to automate tool selection.
*   **Key Features:**
    *   **Aggregation:** One endpoint for multiple servers.
    *   **Budgeting:** Limit exposed tools based on presets (minimal, development, full).
    *   **Routing:** Directs calls to the appropriate underlying server.

## Building and Running

The project uses **Docker Compose** and a **Makefile** for orchestration.

### Prerequisites
*   Docker & Docker Compose
*   Python 3.10+ (for local dev)

### Key Commands

Run these from the project root:

| Command | Description |
| :--- | :--- |
| `make start` | Start all services (Gateway + UI + MCP Servers). |
| `make stop` | Stop all services. |
| `make restart` | Restart all services. |
| `make logs` | Follow logs from all services. |
| `make logs-gateway` | Follow gateway logs only. |
| `make logs-ui` | Follow UI logs only. |
| `make build` | Rebuild containers. |
| `make clean` | Stop and remove containers, networks, and volumes (clears state). |
| `make reset` | Reset tool configuration to the default "development" preset. |
| `make install-agents` | Install AI agent definitions to `~/.claude/agents/`. |
| `make status` | Show status of running services and endpoints. |

### Access Points
*   **Gateway API:** `http://localhost:8090` (MCP endpoint: `/mcp`)
*   **Tool Selector UI:** `http://localhost:5010`

## Configuration

1.  **Environment:** Copy `.env.example` to `.env` and configure keys (e.g., `GITHUB_TOKEN`, `PERPLEXITY_API_KEY`).
2.  **MCP Servers:** Defined in `servers/<server_name>/config.json`.
3.  **Presets:** Tool budgets defined in `presets/` (e.g., `development.json`).

## Development Conventions

*   **Tool Naming:** Tools are namespaced: `{server}__{tool_name}` (e.g., `github__search_code`).
*   **State:** Tool enabled/disabled state is persisted in a Docker volume (`btr-data`).
*   **Adding Servers:**
    1.  Create `servers/<name>/config.json`.
    2.  Add the service to `docker-compose.yml`.
    3.  Add keys to `.env`.
    4.  Restart services.

## Directory Structure

*   `gateway/`: Core routing logic (FastAPI).
*   `ui/`: Management dashboard (Flask).
*   `servers/`: Configuration for upstream MCP servers.
*   `presets/`: JSON files defining groups of enabled tools.
*   `docs/`: Detailed documentation (`ARCHITECTURE.md`, `CONFIGURATION.md`).

## MCP Tools (BTR)

<!-- BTR_TOOLS_START -->
**Last Updated:** 2025-12-27 UTC
**Currently Enabled:** 12 tools

| Server | Tools | Purpose |
|--------|-------|---------|
| **GitHub** | `create_issue`, `list_issues`, `issue_read`, `create_pull_request`, `list_pull_requests`, `pull_request_read`, `get_file_contents`, `create_or_update_file`, `push_files` | VCS operations for github.com/IMUR/mcp-btr |
| **Perplexity** | `perplexity_ask`, `perplexity_reason`, `perplexity_research` | Research Python/FastAPI patterns, Docker, MCP protocol |

**Why This Configuration:**
- Tech stack: Python (FastAPI/Flask), Docker, MCP protocol implementation
- VCS: GitHub (github.com/IMUR/mcp-btr)
- Excluded: Gitea (wrong platform), Svelte/Ark-UI (no frontend frameworks), ElevenLabs (no audio), Mapbox (no geo)
<!-- BTR_TOOLS_END -->
