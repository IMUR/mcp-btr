"""
Stdio Transport - Communicates with MCP servers via local subprocess
"""
import os
import json
import asyncio
import shutil
from typing import Any

from .base import Transport, TransportError, TransportConnectionError, TransportTimeoutError


class StdioTransport(Transport):
    """
    Transport that spawns a local subprocess for MCP communication.

    Supports direct execution of:
    - npx packages: ["npx", "-y", "@github/mcp-server"]
    - Python modules: ["python", "-m", "perplexity_mcp"]
    - Binaries: ["/path/to/mcp-server", "--stdio"]

    Config schema:
    {
        "command": ["npx", "-y", "@github/mcp-server"],
        "env": {"VAR": "value"},
        "cwd": "/optional/working/dir",
        "timeout": 30.0
    }
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.command = config.get("command", [])
        self.env = config.get("env", {})
        self.cwd = config.get("cwd")

        if not self.command:
            raise ValueError("Stdio transport requires 'command' in config")

    def _build_env(self) -> dict:
        """Build environment dict with expanded variables"""
        # Start with current environment
        env = dict(os.environ)

        # Add/override with config env vars
        for key, value in self.env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                # Support default values: ${VAR:-default}
                if ":-" in env_name:
                    env_name, default = env_name.split(":-", 1)
                    value = os.environ.get(env_name, default)
                else:
                    value = os.environ.get(env_name, "")
            env[key] = value

        return env

    async def send_request(self, request: dict) -> dict:
        """
        Send JSON-RPC request via subprocess stdin/stdout.

        Args:
            request: JSON-RPC request dict

        Returns:
            JSON-RPC response dict
        """
        env = self._build_env()

        try:
            proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.cwd
            )

            request_bytes = json.dumps(request).encode() + b"\n"

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(request_bytes),
                timeout=self.timeout
            )

            if proc.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                raise TransportConnectionError(
                    f"Process failed (exit {proc.returncode}): {error_msg}",
                    {"command": self.command, "stderr": error_msg}
                )

            if not stdout:
                raise TransportError(
                    "Empty response from MCP server",
                    {"command": self.command}
                )

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            raise TransportTimeoutError(
                f"Request timed out after {self.timeout}s",
                {"command": self.command}
            )
        except json.JSONDecodeError as e:
            raise TransportError(
                f"Invalid JSON response: {e}",
                {"command": self.command, "raw": stdout.decode() if stdout else ""}
            )
        except FileNotFoundError:
            raise TransportConnectionError(
                f"Command not found: {self.command[0]}",
                {"command": self.command}
            )
        except PermissionError:
            raise TransportConnectionError(
                f"Permission denied executing: {self.command[0]}",
                {"command": self.command}
            )

    async def is_available(self) -> bool:
        """Check if the command is available"""
        if not self.command:
            return False

        executable = self.command[0]

        # Check if it's an absolute path
        if os.path.isabs(executable):
            return os.path.isfile(executable) and os.access(executable, os.X_OK)

        # Check if it's in PATH
        return shutil.which(executable) is not None
