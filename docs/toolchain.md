# Toolchain (MCP-BTR development)

This document describes the minimal toolchain to develop, run, and distribute **MCP-BTR (Budgeted Tool Router)** as a self-contained stack built on top of **MCPJungle** tool groups.

This is intentionally practical: what you need installed, what runs where, and how to verify changes end-to-end without leaking secrets.

## Architecture at a glance

MCP-BTR is best treated as a **control plane** that publishes a **budgeted tool surface** (MCP tool groups) for clients to consume.

- **MCPJungle**: Gateway/registry that exposes MCP endpoints and tool groups.
- **Tool selector UI/API**: Human-driven selection that updates the `basic` group (current system pattern).
- **BTR engine (planned product component)**: Context detection + routing/budgeting/brokering + reset semantics (environment-agnostic version of the Claude subagents).
- **Optional local LLM runtime**: Only needed if you want model-assisted classification. The deterministic rules must work without it.

See also:
- `docs/mcp/QUICKSTART.md` for stack bring-up and endpoints.
- `docs/mcp/TOOL_SELECTOR.md` for the current UI/API behavior.
- `docs/mcp/mcp-tool-selector.md` and `docs/mcp/mcp-tools-reset.md` for the agent logic we’re productizing.
- `docs/mcp/HTTPS_ENDPOINTS.md` for the HTTPS reverse-proxy layout.

## Required tools (development + operations)

- **Docker + Docker Compose**: Runs MCPJungle, tool selector, and any MCP servers you unify behind the gateway.
- **curl**: Quick endpoint checks and API usage.
- **jq**: Optional but strongly recommended for inspecting JSON responses.
- **Node.js + npx**: Used for Markdown linting (`npx markdownlint "**/*.md"`).

## Optional tools (recommended for production parity)

- **Infisical CLI**: Used to inject secrets at runtime so no tokens land in git history.
- **Caddy (or equivalent reverse proxy)**: Used when you expose the stack via a single HTTPS domain.

## Project conventions

- **No secrets in git**: Treat all API keys as runtime secrets (Infisical, environment variables, or external secret managers).
- **Docs live under `docs/`**: Keep the repository root small and stable.
- **Minimal coherent change**: Prefer adding a small BTR layer that drives MCPJungle over forking/replacing MCPJungle.

## Local development workflow

Use this loop when changing selection logic, reset behavior, or the frontend control surface:

- **Bring up the stack**: Follow `docs/mcp/QUICKSTART.md`.
- **Inspect available tools**:
  - `GET /api/tools` (tool selector API)
  - `POST tools/list` via the MCP group endpoint you’re targeting
- **Apply a budgeted selection**:
  - Use the UI (manual) or the BTR engine (automatic) to compute a minimal tool set.
  - Publish the set by updating a tool group endpoint (for example, `basic`).
- **Verify client-visible results**:
  - Confirm the group endpoint only returns the selected tools.
  - Confirm at least one representative tool call works end-to-end.

## Reset workflow (product requirement)

The “reset” capability should be a first-class operation, not a prompt trick:

- **Group reset**: Set a group’s tool list to empty (or a default baseline).
- **Doc reset**: Update documentation markers (where used) to reflect the clean state.
- **Optional “factory reset”**: Delete or recreate groups as needed to match desired invariants.

The current reset semantics are captured in `docs/mcp/mcp-tools-reset.md` and should be implemented as API/CLI operations in MCP-BTR.

## Tool routing and budgeting workflow (product requirement)

MCP-BTR should expose an environment-agnostic interface that does the following:

- **Discovery**: Enumerate tools from MCPJungle and cache tool metadata.
- **Context analysis**: Infer project/work context (VCS remote, language ecosystem, declared dependencies).
- **Budgeting**: Enforce global tool count and per-category budgets (VCS/docs/research/etc).
- **Brokering**: Publish the resulting tool surface as an MCPJungle tool group endpoint.
- **Routing**: Return the correct group endpoint to the caller (human or agent) for the current context.

The existing selection logic in `.archive/mcp-tool-selector.md` is the canonical reference for minimum-sufficiency rules and mutual exclusivity (e.g., GitHub vs Gitea).

## Verification checklist

Before considering a change “done”, validate it end-to-end:

- **Gateway health**:
  - `GET /health` on the MCPJungle gateway (local or HTTPS).
- **Tool selector API**:
  - `GET /api/tools` returns tools grouped by server.
  - `GET /api/current` reflects your last update.
- **Group endpoint behavior**:
  - `tools/list` returns only the intended tool subset.
  - At least one `tools/call` succeeds (choose a safe/read-only tool).

## Documentation linting

Before opening a review, lint Markdown:

```bash
npx markdownlint "**/*.md"
```

If linting fails, fix only what you touched unless the fix is trivial and clearly improves consistency.


