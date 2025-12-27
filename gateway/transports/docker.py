"""
Docker Transport - Communicates with MCP servers via docker exec
"""
import os
import json
import asyncio
from typing import Any

from .base import Transport, TransportError, TransportConnectionError, TransportTimeoutError


class DockerTransport(Transport):
    """
    Transport that uses 'docker exec' to communicate with containerized MCP servers.

    Config schema:
    {
        "container": "container-name",
        "command": ["/app/server"],
        "env": {"VAR": "value"},
        "timeout": 30.0
    }
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.container = config.get("container")
        self.command = config.get("command", [])
        self.env = config.get("env", {})

        if not self.container:
            raise ValueError("Docker transport requires 'container' in config")

    def _build_exec_command(self) -> list[str]:
        """Build the docker exec command"""
        cmd = ["docker", "exec", "-i"]

        # Add environment variables
        for key, value in self.env.items():
            # Expand environment variable references
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                # Support default values: ${VAR:-default}
                if ":-" in env_name:
                    env_name, default = env_name.split(":-", 1)
                    value = os.environ.get(env_name, default)
                else:
                    value = os.environ.get(env_name, "")
            cmd.extend(["-e", f"{key}={value}"])

        cmd.append(self.container)
        cmd.extend(self.command)

        return cmd

    async def send_request(self, request: dict) -> dict:
        """
        Send JSON-RPC request via docker exec.

        Args:
            request: JSON-RPC request dict

        Returns:
            JSON-RPC response dict
        """
        cmd = self._build_exec_command()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            request_bytes = json.dumps(request).encode() + b"\n"

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(request_bytes),
                timeout=self.timeout
            )

            if proc.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                raise TransportConnectionError(
                    f"Docker exec failed (exit {proc.returncode}): {error_msg}",
                    {"container": self.container, "stderr": error_msg}
                )

            if not stdout:
                raise TransportError(
                    "Empty response from MCP server",
                    {"container": self.container}
                )

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            raise TransportTimeoutError(
                f"Request timed out after {self.timeout}s",
                {"container": self.container}
            )
        except json.JSONDecodeError as e:
            raise TransportError(
                f"Invalid JSON response: {e}",
                {"container": self.container, "raw": stdout.decode() if stdout else ""}
            )
        except FileNotFoundError:
            raise TransportConnectionError(
                "Docker command not found. Is Docker installed?",
                {"container": self.container}
            )

    async def is_available(self) -> bool:
        """Check if the Docker container is running"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "-f", "{{.State.Running}}", self.container,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            return stdout.decode().strip() == "true"

        except (asyncio.TimeoutError, FileNotFoundError, Exception):
            return False
