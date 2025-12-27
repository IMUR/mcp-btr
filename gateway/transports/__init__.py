"""
BTR Transport Layer - Abstracts MCP server communication
Supports multiple transport modes: Docker exec, local stdio, HTTP
"""
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Transport

__all__ = ["TransportMode", "get_transport"]


class TransportMode(Enum):
    """Supported transport modes for MCP server communication"""
    DOCKER = "docker"    # docker exec -i container command
    LOCAL = "local"      # direct subprocess (npx, python -m, etc.)
    HTTP = "http"        # HTTP-based MCP servers


def get_transport(mode: TransportMode, config: dict) -> "Transport":
    """
    Factory function to create appropriate transport instance.

    Args:
        mode: The transport mode to use
        config: Transport-specific configuration from server config

    Returns:
        Transport instance ready to send requests
    """
    if mode == TransportMode.DOCKER:
        from .docker import DockerTransport
        return DockerTransport(config)
    elif mode == TransportMode.LOCAL:
        from .stdio import StdioTransport
        return StdioTransport(config)
    elif mode == TransportMode.HTTP:
        from .http import HttpTransport
        return HttpTransport(config)
    else:
        raise ValueError(f"Unknown transport mode: {mode}")
