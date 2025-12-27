"""
BTR Error Definitions - User-friendly error messages with troubleshooting hints
"""
from typing import Optional, List


class BTRError(Exception):
    """
    Base BTR error with user-friendly messages and troubleshooting hints.
    """
    def __init__(
        self,
        message: str,
        details: Optional[dict] = None,
        hints: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.hints = hints or []

    def to_dict(self) -> dict:
        """Convert error to dictionary for API responses"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "hints": self.hints
        }


class ServerConnectionError(BTRError):
    """
    MCP server connection failed.

    Common causes:
    - Container not running (docker mode)
    - Command not found (local mode)
    - Network connectivity issues (http mode)
    """
    def __init__(
        self,
        server_name: str,
        transport: str,
        cause: Optional[str] = None,
        details: Optional[dict] = None
    ):
        hints = []

        if transport == "docker":
            hints = [
                f"Check if container '{server_name}-mcp' is running: docker ps | grep {server_name}",
                f"Start the container: docker compose up -d {server_name}-mcp",
                "View container logs: docker compose logs {server_name}-mcp",
                "Ensure Docker socket is accessible to the gateway"
            ]
        elif transport == "local":
            hints = [
                "Check if the command is installed and in PATH",
                "For npx commands: ensure Node.js is installed",
                "For Python modules: ensure the package is installed",
                "Check environment variables are set correctly"
            ]
        elif transport == "http":
            hints = [
                "Check if the MCP server is running and accessible",
                "Verify the URL is correct",
                "Check firewall and network connectivity"
            ]

        message = f"Failed to connect to MCP server '{server_name}' via {transport}"
        if cause:
            message += f": {cause}"

        super().__init__(message, details, hints)
        self.server_name = server_name
        self.transport = transport


class ToolNotEnabledError(BTRError):
    """
    Tool call rejected because tool is not in enabled set.
    """
    def __init__(self, tool_name: str, server_name: Optional[str] = None):
        hints = [
            f"Enable via UI: http://localhost:5010 -> Find and toggle '{tool_name}'",
            f"Enable via API: POST /api/tools/enable {{\"tool\": \"{tool_name}\"}}",
            "Use btr-tool-selector agent to auto-configure tools",
            "Load a preset: POST /api/presets/load {\"name\": \"development\"}"
        ]

        super().__init__(
            f"Tool '{tool_name}' is not enabled",
            {"tool": tool_name, "server": server_name},
            hints
        )
        self.tool_name = tool_name


class ToolNotFoundError(BTRError):
    """
    Tool does not exist in any registered server.
    """
    def __init__(self, tool_name: str, available_servers: Optional[List[str]] = None):
        hints = [
            "Check the tool name is correct (format: server__tool_name)",
            "List available tools: GET /api/tools",
            "Verify the MCP server providing this tool is configured"
        ]

        if available_servers:
            hints.append(f"Available servers: {', '.join(available_servers)}")

        super().__init__(
            f"Unknown tool: '{tool_name}'",
            {"tool": tool_name},
            hints
        )
        self.tool_name = tool_name


class ConfigurationError(BTRError):
    """
    Configuration is invalid or missing.
    """
    def __init__(self, config_item: str, issue: str, fix: Optional[str] = None):
        hints = []
        if fix:
            hints.append(fix)
        hints.extend([
            "Check .env file for missing variables",
            "Verify file paths in configuration",
            "See docs/CONFIGURATION.md for reference"
        ])

        super().__init__(
            f"Configuration error: {config_item} - {issue}",
            {"config_item": config_item},
            hints
        )


class TransportNotAvailableError(BTRError):
    """
    Requested transport mode is not available for a server.
    """
    def __init__(
        self,
        server_name: str,
        requested_transport: str,
        available_transports: List[str]
    ):
        hints = [
            f"Available transports for {server_name}: {', '.join(available_transports)}",
            f"Set BTR_TRANSPORT_MODE to one of: {', '.join(available_transports)}",
            "Or set BTR_TRANSPORT_MODE=auto to auto-select"
        ]

        super().__init__(
            f"Transport '{requested_transport}' not available for server '{server_name}'",
            {
                "server": server_name,
                "requested": requested_transport,
                "available": available_transports
            },
            hints
        )


class PresetNotFoundError(BTRError):
    """
    Requested preset does not exist.
    """
    def __init__(self, preset_name: str, available_presets: Optional[List[str]] = None):
        hints = [
            "List available presets: GET /api/presets",
            "Create custom preset in presets/ directory"
        ]

        if available_presets:
            hints.insert(0, f"Available presets: {', '.join(available_presets)}")

        super().__init__(
            f"Preset not found: '{preset_name}'",
            {"preset": preset_name},
            hints
        )


class ToolInvocationError(BTRError):
    """
    Tool execution failed.
    """
    def __init__(
        self,
        tool_name: str,
        server_name: str,
        cause: str,
        details: Optional[dict] = None
    ):
        hints = [
            "Check tool arguments are correct",
            "View gateway logs for detailed error",
            f"Verify {server_name} MCP server is healthy: GET /health"
        ]

        super().__init__(
            f"Tool '{tool_name}' failed: {cause}",
            {"tool": tool_name, "server": server_name, **(details or {})},
            hints
        )
