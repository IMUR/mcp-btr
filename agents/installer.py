#!/usr/bin/env python3
"""
BTR Agent Installer - Installs agents to all detected AI platforms
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generator import load_agent_definition, GENERATORS


# Platform detection and installation paths
PLATFORM_CONFIGS = {
    "claude_code": {
        "name": "Claude Code",
        "detection_paths": [
            Path.home() / ".claude",
            Path.home() / ".config" / "claude"
        ],
        "install_dir": Path.home() / ".claude" / "agents",
        "extension": ".md"
    },
    "cursor": {
        "name": "Cursor",
        "detection_paths": [
            Path.home() / ".cursor",
            Path.home() / ".config" / "cursor"
        ],
        "install_dir": Path.home() / ".cursor" / "rules",
        "extension": ".mdc"
    },
    "gemini": {
        "name": "Gemini CLI",
        "detection_paths": [
            Path.home() / ".gemini",
            Path.home() / ".config" / "gemini"
        ],
        "install_dir": Path.home() / ".gemini" / "agents",
        "extension": ".md"
    },
    "openai": {
        "name": "OpenAI CLI",
        "detection_paths": [
            Path.home() / ".openai",
            Path.home() / ".config" / "openai"
        ],
        "install_dir": Path.home() / ".openai" / "functions",
        "extension": ".json"
    },
    "generic": {
        "name": "Generic Scripts",
        "detection_paths": [],  # Always available
        "install_dir": Path.home() / ".btr" / "scripts",
        "extension": ".sh",
        "always_install": True
    }
}


def detect_platforms() -> list[str]:
    """Detect which AI platforms are installed"""
    detected = []

    for platform, config in PLATFORM_CONFIGS.items():
        # Generic is always available
        if config.get("always_install"):
            detected.append(platform)
            continue

        # Check detection paths
        for path in config["detection_paths"]:
            if path.exists():
                detected.append(platform)
                break

    return detected


def install_agent(
    agent_path: Path,
    platform: str,
    force: bool = False
) -> tuple[bool, str]:
    """
    Install an agent for a specific platform.

    Returns:
        (success, message) tuple
    """
    if platform not in PLATFORM_CONFIGS:
        return False, f"Unknown platform: {platform}"

    config = PLATFORM_CONFIGS[platform]
    generator_cls = GENERATORS.get(platform)

    if not generator_cls:
        return False, f"No generator for platform: {platform}"

    try:
        # Load agent definition
        definition = load_agent_definition(agent_path)
        agent_name = definition.get("metadata", {}).get("name", agent_path.stem)

        # Generate content
        generator = generator_cls()
        content = generator.generate(definition)

        # Create install directory
        install_dir = config["install_dir"]
        install_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        output_file = install_dir / f"{agent_name}{config['extension']}"

        if output_file.exists() and not force:
            return True, f"Already exists: {output_file}"

        with open(output_file, "w") as f:
            f.write(content)

        # Make scripts executable
        if config["extension"] == ".sh":
            os.chmod(output_file, 0o755)

        return True, str(output_file)

    except Exception as e:
        return False, f"Error: {e}"


def install_config_file(force: bool = False) -> tuple[bool, str]:
    """Install the BTR configuration file"""
    config_file = Path.home() / ".btr.env"
    example_file = Path(__file__).parent / ".btr.env.example"

    if config_file.exists() and not force:
        return True, f"Already exists: {config_file}"

    # Create default config
    content = """# BTR Agent Configuration
# Edit these values for your BTR deployment

# BTR host (localhost or remote hostname/IP)
BTR_HOST=localhost

# BTR API ports
BTR_UI_PORT=5010
BTR_GATEWAY_PORT=8090
"""

    # If example file exists, use it instead
    if example_file.exists():
        with open(example_file) as f:
            content = f.read()

    with open(config_file, "w") as f:
        f.write(content)

    return True, str(config_file)


def main():
    """Main installer entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="BTR Agent Installer - Install agents to AI platforms"
    )
    parser.add_argument(
        "--platforms",
        type=str,
        help="Comma-separated list of platforms to install to"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files"
    )
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="List available platforms"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without installing"
    )

    args = parser.parse_args()

    # List platforms mode
    if args.list_platforms:
        print("Available platforms:")
        for platform, config in PLATFORM_CONFIGS.items():
            print(f"  {platform}: {config['name']}")
        return

    # Detect or parse platforms
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",")]
    else:
        platforms = detect_platforms()

    print("BTR Agent Installer")
    print("=" * 40)
    print()

    # Detect platforms
    print("Detecting AI platforms...")
    for platform in PLATFORM_CONFIGS:
        config = PLATFORM_CONFIGS[platform]
        if platform in platforms:
            print(f"  [OK] {config['name']}")
        else:
            print(f"  [--] {config['name']} (not found)")
    print()

    if not platforms:
        print("No platforms detected. Use --platforms to specify manually.")
        return 1

    # Find agent definitions
    core_dir = Path(__file__).parent / "core"
    if not core_dir.exists():
        print(f"Error: Agent definitions not found at {core_dir}")
        return 1

    agent_files = list(core_dir.glob("*.agent.yaml"))
    if not agent_files:
        print(f"Error: No agent definitions found in {core_dir}")
        return 1

    print(f"Found {len(agent_files)} agent(s) to install:")
    for af in agent_files:
        print(f"  - {af.stem}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would install to:")
        for platform in platforms:
            config = PLATFORM_CONFIGS[platform]
            print(f"  {platform}: {config['install_dir']}/")
        return 0

    # Install agents
    print("Installing agents...")
    success_count = 0
    for agent_file in agent_files:
        agent_name = agent_file.stem.replace(".agent", "")
        print(f"\n  {agent_name}:")

        for platform in platforms:
            ok, msg = install_agent(agent_file, platform, force=args.force)
            status = "[OK]" if ok else "[FAIL]"
            config = PLATFORM_CONFIGS[platform]
            print(f"    {status} {config['name']}: {msg}")
            if ok:
                success_count += 1

    # Install config file
    print("\nInstalling configuration...")
    ok, msg = install_config_file(force=args.force)
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {msg}")

    # Summary
    print()
    print("=" * 40)
    print(f"Installed {success_count} agent(s) across {len(platforms)} platform(s)")
    print()
    print("Configuration: ~/.btr.env")
    print()
    print("Restart your AI tools to load the new agents.")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
