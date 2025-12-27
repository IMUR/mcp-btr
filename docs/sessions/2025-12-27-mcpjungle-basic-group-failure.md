# MCPJungle Basic Group Registration Failure

**Date:** 2025-12-27
**Status:** Resolved
**Severity:** High (MCP tools unavailable)

## Symptom

All requests to the MCPJungle basic group endpoint returned 404:

```
curl http://localhost:8090/v0/groups/basic/mcp
{"error":"tool group not found: basic"}
```

MCPJungle server logs showed continuous 404 responses:
```
[GIN] 2025/12/27 - 21:08:07 | 404 | POST "/v0/groups/basic/mcp"
```

## Root Cause

The `mcp-tool-selector` subagent (`~/.claude/agents/mcp-tool-selector.md`) contained **hardcoded Gitea-style tool names** as examples. When an agent attempted to configure GitHub tools, it used invalid names:

| In basic.json (wrong) | Actual GitHub tool name |
|-----------------------|------------------------|
| `github__create_issue` | `github__issue_write` |
| `github__list_issues` | `github__list_issues` |
| `github__issue_read` | `github__issue_read` |
| `github__get_file_contents` | `github__get_file_contents` |

The Tool Selector API (`app.py`) has a **destructive update pattern**:

```python
def update_basic_group(selected_tools):
    # Write config
    with open(BASIC_GROUP_FILE, 'w') as f:
        json.dump(group_config, f, indent=2)

    # DELETE existing group first
    exec_mcpjungle(["delete", "group", "basic"])

    # Then create new group (FAILS if tool names invalid)
    result = exec_mcpjungle(["create", "group", "-c", "/groups/basic.json"])
```

When `create group` failed due to invalid tool names, the group was left **permanently deleted**.

## Resolution

### 1. Fixed basic.json with correct tool names

```json
{
  "name": "basic",
  "included_tools": [
    "perplexity__perplexity_ask",
    "perplexity__perplexity_reason",
    "perplexity__perplexity_research",
    "gitea__create_issue",
    "gitea__list_repo_issues",
    "gitea__get_issue_by_index",
    "gitea__create_pull_request",
    "gitea__list_repo_pull_requests",
    "gitea__get_pull_request_by_index",
    "gitea__get_file_content",
    "gitea__create_file",
    "gitea__update_file"
  ]
}
```

### 2. Re-registered the basic group

```bash
docker exec mcpjungle-server /mcpjungle create group -c /groups/basic.json
```

### 3. Updated mcp-tool-selector.md for dynamic discovery

Removed hardcoded tool names and added explicit instructions:

```markdown
**CRITICAL: Tool names differ between platforms. Always discover actual names from API:**

# Get exact tool names for the detected VCS platform
ssh crtr "curl -s http://localhost:5010/api/tools" | jq -r '.servers.gitea[].name'
ssh crtr "curl -s http://localhost:5010/api/tools" | jq -r '.servers.github[].name'
```

## Verification

```bash
# Group now registered
docker exec mcpjungle-server /mcpjungle list groups | grep basic
# Output: 6. basic - User-selected basic tools (configured via web UI)

# Endpoint working (200 responses in logs)
docker logs mcpjungle-server --tail 5
# [GIN] 2025/12/27 - 21:42:41 | 200 | POST "/v0/groups/basic/mcp"

# Tools correctly loaded
curl -s http://localhost:5010/api/current | jq '.tools | length'
# Output: 12
```

## Prevention

1. **Subagent instructions** now require dynamic tool discovery before selection
2. **Tool names** must be validated against API response, not assumed from examples
3. **Consider fixing** `app.py` to use atomic update (create new, then delete old) instead of delete-first pattern

## Files Modified

| File | Change |
|------|--------|
| `/media/crtr/fortress/docker/MCPJungle/groups/basic.json` | Fixed tool names |
| `~/.claude/agents/mcp-tool-selector.md` | Dynamic discovery instructions |

## Related

- Tool Selector UI: http://localhost:5010
- MCPJungle endpoint: http://localhost:8090/v0/groups/basic/mcp
- Tool Selector source: `/media/crtr/fortress/docker/MCPJungle/tool-selector/app.py`
