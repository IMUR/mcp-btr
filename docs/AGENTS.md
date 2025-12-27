# BTR AI Selection Agents

How the AI agents automate tool selection based on project context.

## Overview

BTR includes two AI agents that integrate with Claude Code (and compatible tools):

| Agent | Purpose |
|-------|---------|
| `btr-tool-selector` | Analyzes project context and configures optimal tools |
| `btr-tools-reset` | Resets to clean state |

## Installation

Run the installer:

```bash
./agents/install.sh
```

This copies agents to `~/.claude/agents/` and creates `~/.btr.env`.

## Configuration

Agents read from `~/.btr.env`:

```bash
# BTR host (localhost or remote)
BTR_HOST=localhost

# API ports
BTR_UI_PORT=5010
BTR_GATEWAY_PORT=8090
```

For remote BTR deployments, set `BTR_HOST` to the server's hostname or IP.

## Using btr-tool-selector

This agent analyzes your project and automatically configures tools.

### When to Use

- Starting work on a new project
- Switching between projects
- When tool selection seems suboptimal

### What It Analyzes

1. **VCS Platform**
   - Reads `git remote -v`
   - Enables GitHub or Gitea tools accordingly

2. **Technology Stack**
   - `package.json` → Svelte, React, Vue, etc.
   - `pyproject.toml` → Python frameworks
   - `go.mod` → Go projects
   - `Cargo.toml` → Rust projects

3. **Project Instructions**
   - Reads `CLAUDE.md`, `GEMINI.md` for explicit requirements

4. **Directory Structure**
   - Detects patterns like `src/routes/` (SvelteKit), `pages/` (Next.js)

### Tool Budgeting

The agent follows the "Principle of Minimal Sufficiency":

| Budget | Tools | When |
|--------|-------|------|
| Minimal | 5-10 | Quick tasks, simple edits |
| Optimal | 15-30 | Typical development |
| Maximum | 30-40 | Complex multi-service work |

Going over 40 tools requires explicit justification.

### Example Output

```
Configured 21 tools: GitHub (9), Perplexity (3), Svelte (4), Ark UI (5).
Excluded: Gitea (using GitHub), audio, and mapping tools.
```

## Using btr-tools-reset

Clears all tool selections and updates documentation.

### When to Use

- Before switching to a very different project
- When tool selection has become cluttered
- Before running btr-tool-selector fresh

### What It Does

1. Disables all tools via API
2. Verifies the reset
3. Updates MCP Tools sections in project markdown files
4. Reports next steps

## Documentation Updates

Both agents update the MCP Tools section in these files (if they exist):

- `CLAUDE.md`
- `GEMINI.md`
- `AGENTS.md`

The updated section looks like:

```markdown
## MCP Tools (BTR)

<!-- BTR_TOOLS_START -->
**Last Updated:** 2025-01-15 10:30 UTC
**Currently Enabled:** 21 tools

| Server | Tools | Purpose |
|--------|-------|---------|
| **github** | `search_code`, `get_file_contents`, ... | Version control |
| **perplexity** | `perplexity_ask`, `perplexity_research` | Research |

**Why This Configuration:**
- Tech stack: SvelteKit, Ark UI
- VCS: GitHub (detected from remote)
- Excluded: Gitea, audio, mapping
<!-- BTR_TOOLS_END -->
```

## Manual vs Automatic

| Approach | Pros | Cons |
|----------|------|------|
| **UI (manual)** | Full control, visual feedback | Requires manual selection |
| **Agents (auto)** | Fast, context-aware, consistent | May not match preferences exactly |
| **Both** | Agent sets baseline, UI for tweaks | Best of both worlds |

## Troubleshooting

### Agent can't connect to BTR

1. Check BTR is running:
   ```bash
   curl http://localhost:5010/health
   ```

2. Verify `~/.btr.env` has correct values

3. For remote BTR, ensure network connectivity

### Agent makes wrong tool choices

1. Check what it detected:
   - Look at the analysis output
   - Verify git remotes, package files

2. Override manually:
   - Use Tool Selector UI
   - Add explicit instructions to `CLAUDE.md`

### Documentation not updating

1. Ensure markdown files exist in project root
2. Check for proper section headers (`## MCP Tools`)
3. Verify file permissions
