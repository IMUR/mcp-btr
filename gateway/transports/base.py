"""
Base Transport class - Abstract interface for MCP server communication
"""
import json
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class TransportConfig:
    """Base configuration for transports"""
    timeout: float = 30.0


class Transport(ABC):
    """
    Abstract base class for MCP transport implementations.

    Each transport handles communication with MCP servers using
    a specific protocol (Docker exec, stdio subprocess, HTTP).
    """

    def __init__(self, config: dict):
        """
        Initialize transport with configuration.

        Args:
            config: Transport-specific configuration dict
        """
        self.config = config
        self.timeout = config.get("timeout", 30.0)

    @abstractmethod
    async def send_request(self, request: dict) -> dict:
        """
        Send a JSON-RPC request to the MCP server.

        Args:
            request: JSON-RPC request dict with method, params, id

        Returns:
            JSON-RPC response dict

        Raises:
            TransportError: If communication fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if this transport is available/configured correctly.

        Returns:
            True if transport can be used, False otherwise
        """
        pass

    async def get_tools(self) -> list[dict]:
        """
        Convenience method to get tools from MCP server.

        Returns:
            List of tool definitions
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        response = await self.send_request(request)
        return response.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """
        Convenience method to call a tool on the MCP server.

        Args:
            name: Tool name (without server prefix)
            arguments: Tool arguments

        Returns:
            Tool result
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        response = await self.send_request(request)

        if "error" in response:
            raise TransportError(
                f"Tool call failed: {response['error'].get('message', 'Unknown error')}"
            )

        return response.get("result")


class TransportError(Exception):
    """Base exception for transport errors"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


class TransportConnectionError(TransportError):
    """Raised when transport cannot connect to MCP server"""
    pass


class TransportTimeoutError(TransportError):
    """Raised when transport request times out"""
    pass
