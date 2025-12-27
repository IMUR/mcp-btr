"""
BTR Tool Router - Filters tools based on enabled state
"""
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from config import settings, tool_state


@dataclass
class MCPServer:
    """Represents a registered MCP server"""
    name: str
    description: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    tools: list[dict] = field(default_factory=list)


class ToolRouter:
    """Routes MCP requests to appropriate servers, filtering by enabled tools"""

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self.all_tools: dict[str, dict] = {}  # tool_name -> {server, schema}
        self._load_servers()

    def _load_servers(self):
        """Load MCP server configurations from servers/ directory"""
        if not settings.servers_dir.exists():
            return

        for server_dir in settings.servers_dir.iterdir():
            if not server_dir.is_dir():
                continue

            config_file = server_dir / "config.json"
            if not config_file.exists():
                continue

            try:
                with open(config_file) as f:
                    config = json.load(f)

                server = MCPServer(
                    name=config["name"],
                    description=config.get("description", ""),
                    command=config["command"],
                    env=config.get("env", {})
                )
                self.servers[server.name] = server

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load server config {config_file}: {e}")

    async def discover_tools(self) -> dict[str, list[dict]]:
        """Discover all tools from all registered servers"""
        tools_by_server = {}

        for name, server in self.servers.items():
            try:
                tools = await self._get_server_tools(server)
                tools_by_server[name] = tools

                # Index tools for routing
                for tool in tools:
                    tool_name = f"{name}__{tool['name']}"
                    self.all_tools[tool_name] = {
                        "server": name,
                        "original_name": tool["name"],
                        "schema": tool
                    }

            except Exception as e:
                print(f"Warning: Failed to discover tools from {name}: {e}")
                tools_by_server[name] = []

        return tools_by_server

    async def _get_server_tools(self, server: MCPServer) -> list[dict]:
        """Get tools from a specific MCP server via stdio"""
        # Send tools/list request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                *server.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**dict(os.environ), **server.env}
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(json.dumps(request).encode() + b"\n"),
                timeout=30.0
            )

            response = json.loads(stdout.decode())
            return response.get("result", {}).get("tools", [])

        except asyncio.TimeoutError:
            print(f"Timeout getting tools from {server.name}")
            return []
        except Exception as e:
            print(f"Error getting tools from {server.name}: {e}")
            return []

    def get_enabled_tools(self) -> list[dict]:
        """Get list of currently enabled tools with their schemas"""
        enabled = []
        for tool_name in tool_state.get_enabled():
            if tool_name in self.all_tools:
                tool_info = self.all_tools[tool_name]
                schema = tool_info["schema"].copy()
                schema["name"] = tool_name  # Use prefixed name
                enabled.append(schema)
        return enabled

    def get_all_tools(self) -> list[dict]:
        """Get all available tools (for UI display)"""
        all_tools = []
        for tool_name, tool_info in self.all_tools.items():
            schema = tool_info["schema"].copy()
            schema["name"] = tool_name
            schema["server"] = tool_info["server"]
            schema["enabled"] = tool_state.is_enabled(tool_name)
            all_tools.append(schema)
        return sorted(all_tools, key=lambda t: t["name"])

    async def invoke_tool(self, tool_name: str, arguments: dict) -> Any:
        """Invoke a tool on its server"""
        if tool_name not in self.all_tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        if not tool_state.is_enabled(tool_name):
            raise ValueError(f"Tool not enabled: {tool_name}")

        tool_info = self.all_tools[tool_name]
        server = self.servers[tool_info["server"]]

        # Send tools/call request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_info["original_name"],
                "arguments": arguments
            }
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                *server.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**dict(os.environ), **server.env}
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(json.dumps(request).encode() + b"\n"),
                timeout=60.0
            )

            response = json.loads(stdout.decode())

            if "error" in response:
                raise Exception(response["error"].get("message", "Unknown error"))

            return response.get("result")

        except asyncio.TimeoutError:
            raise Exception(f"Timeout invoking {tool_name}")


# Need to import os for environment handling
import os

# Global router instance
router = ToolRouter()
