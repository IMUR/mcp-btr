# Repository Guidelines

## Project Structure & Module Organization
- `gateway/` contains the FastAPI gateway (HTTP + SSE MCP endpoint) and tool routing logic.
- `ui/` hosts the Flask UI (`ui/app.py`) and frontend assets (`ui/templates/`, `ui/static/`).
- `presets/` stores tool budgets as JSON files (e.g., `presets/development.json`).
- `servers/` holds MCP server definitions and configs (e.g., `servers/github/config.json`).
- `agents/` includes selection agents and installer scripts; `docs/` contains design and usage docs.
- Root tooling: `docker-compose.yml`, `Makefile`, and `setup.sh` orchestrate local runs.

## Build, Test, and Development Commands
- `./setup.sh` initializes `.env`, builds containers, starts services, and installs agents.
- `make start|stop|restart` controls the stack via Docker Compose.
- `make logs` (or `make logs-gateway`, `make logs-ui`) tails service logs.
- `make build` rebuilds containers; `make clean` removes containers/volumes.
- `make reset` loads the default preset via the UI API.

## Coding Style & Naming Conventions
- Python uses 4-space indentation and snake_case; JS uses 4-space indentation and camelCase.
- Keep module-level docstrings and section headers consistent with existing files.
- Preset names are lowercase; keep JSON keys stable and descriptive.
- Configuration is driven by `.env` and `BTR_*` variables; document new env vars.

## Testing Guidelines
- No automated test suite is present. Validate changes manually:
  - `make start`, then check `http://localhost:8090/health` and `http://localhost:5010/health`.
  - Verify UI behavior and tool lists in the browser.
- If you add tests, note how to run them in this document.

## Commit & Pull Request Guidelines
- Commit history is minimal; use short, imperative subjects (e.g., "Add gateway preset endpoint").
- PRs should include: a clear summary, validation steps, and UI screenshots for frontend changes.
- Note any `.env` or preset changes and include migration steps if needed.

## Agent-Specific Instructions
- The BTR agents may update MCP Tools sections in `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md`.
  Avoid manual edits in those sections unless required.

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
