#!/usr/bin/env python3
"""
BTR Port Checker - Detects port conflicts before starting services
"""
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PortConflict:
    """Represents a port conflict"""
    port: int
    service_name: str
    process_name: Optional[str] = None
    pid: Optional[int] = None


def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a port is available for binding.

    Returns:
        True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Non-zero means connection failed = port available
    except Exception:
        return True  # Assume available if we can't check


def get_process_using_port(port: int) -> Optional[tuple]:
    """
    Get information about the process using a port.

    Returns:
        (process_name, pid) tuple or None if not found
    """
    try:
        # Try lsof (Linux/Mac)
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip().split()[0])

            # Get process name
            name_result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
                timeout=5
            )
            process_name = name_result.stdout.strip() if name_result.returncode == 0 else "unknown"
            return (process_name, pid)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    try:
        # Try ss (Linux)
        result = subprocess.run(
            ["ss", "-tlnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if f":{port}" in line:
                    # Parse process info from ss output
                    if "pid=" in line:
                        import re
                        match = re.search(r'pid=(\d+)', line)
                        if match:
                            return ("process", int(match.group(1)))
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return None


def check_btr_ports(
    gateway_port: int = 8090,
    ui_port: int = 5010
) -> List[PortConflict]:
    """
    Check if BTR ports are available.

    Returns:
        List of PortConflict objects for any ports in use
    """
    conflicts = []

    ports_to_check = [
        (gateway_port, "BTR Gateway"),
        (ui_port, "BTR UI"),
    ]

    for port, service_name in ports_to_check:
        if not check_port_available(port):
            process_info = get_process_using_port(port)
            conflict = PortConflict(
                port=port,
                service_name=service_name,
                process_name=process_info[0] if process_info else None,
                pid=process_info[1] if process_info else None
            )
            conflicts.append(conflict)

    return conflicts


def format_conflict_message(conflicts: List[PortConflict]) -> str:
    """Format port conflicts as a user-friendly message"""
    if not conflicts:
        return "All ports are available."

    lines = ["Port conflicts detected:", ""]

    for conflict in conflicts:
        line = f"  Port {conflict.port} ({conflict.service_name}): "
        if conflict.process_name and conflict.pid:
            line += f"in use by {conflict.process_name} (PID {conflict.pid})"
        else:
            line += "in use by another process"
        lines.append(line)

    lines.extend([
        "",
        "To resolve:",
        "  1. Stop the conflicting process, or",
        "  2. Change BTR ports in .env:",
        f"     BTR_GATEWAY_PORT={conflicts[0].port + 1 if conflicts[0].port == 8090 else 8090}",
        f"     BTR_UI_PORT={conflicts[0].port + 1 if conflicts[0].port == 5010 else 5010}",
    ])

    return "\n".join(lines)


def main():
    """CLI entry point"""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Check if BTR ports are available"
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=int(os.environ.get("BTR_GATEWAY_PORT", 8090)),
        help="Gateway port to check (default: 8090)"
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=int(os.environ.get("BTR_UI_PORT", 5010)),
        help="UI port to check (default: 5010)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output if there are conflicts"
    )

    args = parser.parse_args()

    conflicts = check_btr_ports(args.gateway_port, args.ui_port)

    if conflicts:
        print(format_conflict_message(conflicts))
        sys.exit(1)
    elif not args.quiet:
        print(f"Ports {args.gateway_port} and {args.ui_port} are available.")
        sys.exit(0)


if __name__ == "__main__":
    main()
