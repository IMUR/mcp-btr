"""
HTTP Transport - Communicates with MCP servers via HTTP
"""
import json
import asyncio
from typing import Any, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .base import Transport, TransportError, TransportConnectionError, TransportTimeoutError


class HttpTransport(Transport):
    """
    Transport that communicates with HTTP-based MCP servers.

    Config schema:
    {
        "url": "http://localhost:3000/mcp",
        "headers": {"Authorization": "Bearer ${TOKEN}"},
        "timeout": 30.0
    }
    """

    def __init__(self, config: dict):
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for HTTP transport. "
                "Install with: pip install httpx"
            )

        super().__init__(config)
        self.url = config.get("url")
        self.headers = self._expand_headers(config.get("headers", {}))

        if not self.url:
            raise ValueError("HTTP transport requires 'url' in config")

        self._client: Optional[httpx.AsyncClient] = None

    def _expand_headers(self, headers: dict) -> dict:
        """Expand environment variables in header values"""
        import os
        expanded = {}
        for key, value in headers.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                if ":-" in env_name:
                    env_name, default = env_name.split(":-", 1)
                    value = os.environ.get(env_name, default)
                else:
                    value = os.environ.get(env_name, "")
            expanded[key] = value
        return expanded

    async def _get_client(self) -> "httpx.AsyncClient":
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers
            )
        return self._client

    async def send_request(self, request: dict) -> dict:
        """
        Send JSON-RPC request via HTTP POST.

        Args:
            request: JSON-RPC request dict

        Returns:
            JSON-RPC response dict
        """
        client = await self._get_client()

        try:
            response = await client.post(
                self.url,
                json=request,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code >= 400:
                raise TransportConnectionError(
                    f"HTTP error {response.status_code}: {response.text}",
                    {"url": self.url, "status": response.status_code}
                )

            return response.json()

        except httpx.TimeoutException:
            raise TransportTimeoutError(
                f"Request timed out after {self.timeout}s",
                {"url": self.url}
            )
        except httpx.ConnectError as e:
            raise TransportConnectionError(
                f"Failed to connect to {self.url}: {e}",
                {"url": self.url}
            )
        except json.JSONDecodeError as e:
            raise TransportError(
                f"Invalid JSON response: {e}",
                {"url": self.url}
            )

    async def is_available(self) -> bool:
        """Check if the HTTP endpoint is reachable"""
        try:
            client = await self._get_client()
            response = await client.get(
                self.url.rsplit("/", 1)[0] + "/health",  # Try /health endpoint
                timeout=5.0
            )
            return response.status_code < 500
        except Exception:
            # Try the main URL with a simple request
            try:
                client = await self._get_client()
                response = await client.post(
                    self.url,
                    json={"jsonrpc": "2.0", "id": 0, "method": "initialize"},
                    timeout=5.0
                )
                return response.status_code < 500
            except Exception:
                return False

    async def close(self):
        """Close the HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
