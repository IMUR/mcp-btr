"""
BTR Gateway - Main FastAPI application
Serves MCP tools over HTTP with SSE transport
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from config import settings, tool_state
from router import router

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Track startup time
_startup_time: float = 0


def validate_configuration() -> list[str]:
    """
    Validate configuration before startup.
    Returns list of warning messages.
    """
    warnings = []

    # Check servers directory
    if not settings.servers_dir.exists():
        warnings.append(f"Servers directory not found: {settings.servers_dir}")

    # Check presets directory
    if not settings.presets_dir.exists():
        warnings.append(f"Presets directory not found: {settings.presets_dir}")

    # Check data directory is writable
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        test_file = settings.data_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        warnings.append(f"Data directory not writable: {e}")

    return warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - validate config and discover tools on startup"""
    global _startup_time
    _startup_time = time.time()

    logger.info("BTR Gateway starting...")
    logger.info(f"Transport mode: {settings.transport_mode}")

    # Validate configuration
    warnings = validate_configuration()
    for warning in warnings:
        logger.warning(f"Configuration: {warning}")

    # Discover tools from all servers
    await router.discover_tools()

    # Report startup status
    healthy_count = sum(1 for s in router.servers.values() if s.healthy)
    total_count = len(router.servers)

    logger.info(
        f"Discovered {len(router.all_tools)} tools from "
        f"{healthy_count}/{total_count} healthy servers"
    )
    logger.info(f"Enabled tools: {len(tool_state.get_enabled())}")

    if healthy_count == 0 and total_count > 0:
        logger.warning(
            "No healthy MCP servers! Check server configurations and "
            "ensure containers are running (docker mode) or "
            "commands are available (local mode)."
        )

    startup_duration = time.time() - _startup_time
    logger.info(f"Gateway ready in {startup_duration:.2f}s")

    yield

    logger.info("BTR Gateway shutting down...")


app = FastAPI(
    title="MCP-BTR Gateway",
    description="Budgeted Tool Router - Context-aware MCP tool aggregation",
    version="0.2.0",
    lifespan=lifespan
)

# Enable CORS for UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MCP Protocol Endpoint (JSON-RPC over HTTP SSE)
# =============================================================================

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    MCP JSON-RPC endpoint
    Handles: initialize, tools/list, tools/call
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    logger.debug(f"MCP request: {method}")

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "mcp-btr",
                    "version": "0.2.0"
                }
            }

        elif method == "tools/list":
            tools = router.get_enabled_tools()
            result = {"tools": tools}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                raise ValueError("Missing tool name")

            result = await router.invoke_tool(tool_name, arguments)

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        })

    except ValueError as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": str(e)
            }
        })
    except Exception as e:
        logger.exception(f"Error handling {method}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        })


# =============================================================================
# Management API (for Tool Selector UI and agents)
# =============================================================================

class ToolUpdate(BaseModel):
    tools: list[str]


class ToolToggle(BaseModel):
    tool: str


class PresetLoad(BaseModel):
    name: str


@app.get("/api/tools")
async def get_all_tools():
    """Get all available tools with enabled state"""
    tools = router.get_all_tools()

    # Group by server
    by_server = {}
    for tool in tools:
        server = tool.get("server", "unknown")
        if server not in by_server:
            by_server[server] = []
        by_server[server].append(tool)

    return {
        "success": True,
        "total": len(tools),
        "enabled_count": len(tool_state.get_enabled()),
        "servers": by_server
    }


@app.get("/api/current")
async def get_current():
    """Get currently enabled tools"""
    return {
        "success": True,
        "tools": tool_state.get_enabled(),
        "count": len(tool_state.get_enabled())
    }


@app.post("/api/update")
async def update_tools(update: ToolUpdate):
    """Replace all enabled tools"""
    tool_state.set_tools(update.tools)
    return {
        "success": True,
        "message": f"Updated to {len(update.tools)} tools",
        "tools": tool_state.get_enabled()
    }


@app.post("/api/tools/enable")
async def enable_tool(toggle: ToolToggle):
    """Enable a specific tool"""
    if toggle.tool not in router.all_tools:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {toggle.tool}")

    tool_state.enable_tool(toggle.tool)
    return {"success": True, "tool": toggle.tool, "enabled": True}


@app.post("/api/tools/disable")
async def disable_tool(toggle: ToolToggle):
    """Disable a specific tool"""
    tool_state.disable_tool(toggle.tool)
    return {"success": True, "tool": toggle.tool, "enabled": False}


@app.post("/api/tools/toggle")
async def toggle_tool(toggle: ToolToggle):
    """Toggle a tool's enabled state"""
    if tool_state.is_enabled(toggle.tool):
        tool_state.disable_tool(toggle.tool)
        enabled = False
    else:
        if toggle.tool not in router.all_tools:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {toggle.tool}")
        tool_state.enable_tool(toggle.tool)
        enabled = True

    return {"success": True, "tool": toggle.tool, "enabled": enabled}


@app.get("/api/presets")
async def list_presets():
    """List available presets"""
    presets = []
    if settings.presets_dir.exists():
        for f in settings.presets_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    presets.append({
                        "name": f.stem,
                        "description": data.get("description", ""),
                        "tool_count": len(data.get("tools", []))
                    })
            except (json.JSONDecodeError, IOError):
                continue

    return {"success": True, "presets": presets}


@app.post("/api/presets/load")
async def load_preset(preset: PresetLoad):
    """Load a preset"""
    preset_file = settings.presets_dir / f"{preset.name}.json"
    if not preset_file.exists():
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset.name}")

    try:
        with open(preset_file) as f:
            data = json.load(f)
            tools = data.get("tools", [])
            tool_state.set_tools(tools)

        return {
            "success": True,
            "preset": preset.name,
            "tools": tool_state.get_enabled(),
            "count": len(tool_state.get_enabled())
        }
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load preset: {e}")


@app.get("/health")
async def health():
    """
    Enhanced health check endpoint.
    Returns detailed status of all servers and tools.
    """
    # Calculate uptime
    uptime = time.time() - _startup_time if _startup_time > 0 else 0

    # Get server status
    server_status = router.get_server_status()

    # Determine overall health
    healthy_servers = sum(1 for s in server_status.values() if s.get("healthy"))
    total_servers = len(server_status)

    if total_servers == 0:
        overall_status = "degraded"
    elif healthy_servers == total_servers:
        overall_status = "healthy"
    elif healthy_servers > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "version": "0.2.0",
        "uptime_seconds": round(uptime, 2),
        "transport_mode": settings.transport_mode,
        "servers": server_status,
        "tools": {
            "available": len(router.all_tools),
            "enabled": len(tool_state.get_enabled())
        }
    }


@app.get("/api/status")
async def get_status():
    """
    Detailed status endpoint for debugging and monitoring.
    """
    return {
        "success": True,
        "gateway": {
            "version": "0.2.0",
            "transport_mode": settings.transport_mode,
            "uptime_seconds": round(time.time() - _startup_time, 2) if _startup_time > 0 else 0
        },
        "servers": router.get_server_status(),
        "tools": {
            "available": len(router.all_tools),
            "enabled": len(tool_state.get_enabled()),
            "by_server": {
                name: len([t for t in router.all_tools.values() if t["server"] == name])
                for name in router.servers
            }
        },
        "config": {
            "presets_dir": str(settings.presets_dir),
            "servers_dir": str(settings.servers_dir),
            "data_dir": str(settings.data_dir),
            "default_preset": settings.default_preset
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
