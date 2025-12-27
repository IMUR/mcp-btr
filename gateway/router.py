"""
BTR Tool Router - Filters tools based on enabled state
Supports multiple transport modes for MCP server communication
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from config import settings, tool_state
from transports import TransportMode, get_transport
from transports.base import Transport, TransportError

logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """Represents a registered MCP server with multi-transport support"""
    name: str
    description: str
    default_transport: str
    transports: dict[str, dict] = field(default_factory=dict)
    tools: list[dict] = field(default_factory=list)
    healthy: bool = False
    active_transport: Optional[str] = None

    # Legacy support
    _legacy_command: Optional[list[str]] = None
    _legacy_env: Optional[dict] = None


class ToolRouter:
    """Routes MCP requests to appropriate servers, filtering by enabled tools"""

    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self.all_tools: dict[str, dict] = {}  # tool_name -> {server, schema}
        self._transports: dict[str, Transport] = {}  # server_name -> active transport
        self._load_servers()

    def _load_servers(self):
        """Load MCP server configurations from servers/ directory"""
        if not settings.servers_dir.exists():
            logger.warning(f"Servers directory not found: {settings.servers_dir}")
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

                # Check for new multi-transport schema
                if "transports" in config:
                    server = MCPServer(
                        name=config["name"],
                        description=config.get("description", ""),
                        default_transport=config.get("default_transport", "docker"),
                        transports=config.get("transports", {})
                    )
                # Legacy schema support
                elif "command" in config:
                    server = MCPServer(
                        name=config["name"],
                        description=config.get("description", ""),
                        default_transport="docker",
                        transports={},
                        _legacy_command=config.get("command"),
                        _legacy_env=config.get("env", {})
                    )
                    logger.info(f"Using legacy config for {server.name}")
                else:
                    logger.warning(f"Invalid config for {server_dir.name}: missing transports or command")
                    continue

                self.servers[server.name] = server
                logger.debug(f"Loaded server: {server.name}")

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to load server config {config_file}: {e}")

    def _get_transport_mode(self) -> str:
        """Get the effective transport mode from settings"""
        return settings.transport_mode

    def _select_transport(self, server: MCPServer) -> Optional[Transport]:
        """
        Select and create appropriate transport for a server.

        Args:
            server: MCPServer instance

        Returns:
            Transport instance or None if no transport available
        """
        mode = self._get_transport_mode()

        # Legacy server support
        if server._legacy_command:
            # Detect if legacy command is docker-based
            if server._legacy_command[:2] == ["docker", "exec"]:
                # Extract container name and command
                try:
                    container_idx = server._legacy_command.index("-i") + 1
                    container = server._legacy_command[container_idx]
                    command = server._legacy_command[container_idx + 1:]
                    config = {
                        "container": container,
                        "command": command,
                        "env": server._legacy_env or {}
                    }
                    return get_transport(TransportMode.DOCKER, config)
                except (ValueError, IndexError):
                    logger.error(f"Could not parse legacy docker command for {server.name}")
                    return None
            else:
                # Direct command
                config = {
                    "command": server._legacy_command,
                    "env": server._legacy_env or {}
                }
                return get_transport(TransportMode.LOCAL, config)

        # New multi-transport schema
        if mode == "auto":
            # Try transports in order: docker, local, http
            for try_mode in ["docker", "local", "http"]:
                if try_mode in server.transports:
                    transport_config = server.transports[try_mode]
                    try:
                        transport = get_transport(TransportMode(try_mode), transport_config)
                        server.active_transport = try_mode
                        return transport
                    except Exception as e:
                        logger.debug(f"Transport {try_mode} not available for {server.name}: {e}")
                        continue

            # Fallback to default
            if server.default_transport in server.transports:
                transport_config = server.transports[server.default_transport]
                transport = get_transport(
                    TransportMode(server.default_transport),
                    transport_config
                )
                server.active_transport = server.default_transport
                return transport
        else:
            # Use specified mode
            if mode in server.transports:
                transport_config = server.transports[mode]
                transport = get_transport(TransportMode(mode), transport_config)
                server.active_transport = mode
                return transport
            else:
                logger.warning(
                    f"Transport mode '{mode}' not available for {server.name}. "
                    f"Available: {list(server.transports.keys())}"
                )

        return None

    async def discover_tools(self) -> dict[str, list[dict]]:
        """Discover all tools from all registered servers"""
        tools_by_server = {}

        for name, server in self.servers.items():
            try:
                transport = self._select_transport(server)
                if not transport:
                    logger.warning(f"No transport available for {name}")
                    server.healthy = False
                    tools_by_server[name] = []
                    continue

                self._transports[name] = transport

                # Check availability
                if not await transport.is_available():
                    logger.warning(f"Transport not available for {name}")
                    server.healthy = False
                    tools_by_server[name] = []
                    continue

                # Discover tools
                tools = await transport.get_tools()
                tools_by_server[name] = tools
                server.tools = tools
                server.healthy = True

                # Index tools for routing
                for tool in tools:
                    tool_name = f"{name}__{tool['name']}"
                    self.all_tools[tool_name] = {
                        "server": name,
                        "original_name": tool["name"],
                        "schema": tool
                    }

                logger.info(
                    f"Discovered {len(tools)} tools from {name} "
                    f"(transport: {server.active_transport})"
                )

            except Exception as e:
                logger.error(f"Failed to discover tools from {name}: {e}")
                server.healthy = False
                tools_by_server[name] = []

        return tools_by_server

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
        server_name = tool_info["server"]

        if server_name not in self._transports:
            raise ValueError(f"No transport available for server: {server_name}")

        transport = self._transports[server_name]

        try:
            result = await transport.call_tool(
                tool_info["original_name"],
                arguments
            )
            return result

        except TransportError as e:
            logger.error(f"Tool invocation failed for {tool_name}: {e}")
            raise Exception(f"Tool call failed: {e}")

    def get_server_status(self) -> dict[str, dict]:
        """Get health and transport status for all servers"""
        status = {}
        for name, server in self.servers.items():
            status[name] = {
                "healthy": server.healthy,
                "transport": server.active_transport,
                "tool_count": len(server.tools),
                "available_transports": list(server.transports.keys())
            }
        return status


# Global router instance
router = ToolRouter()
