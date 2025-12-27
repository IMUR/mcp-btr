"""
BTR Agent Generator - Creates platform-specific agent configs from universal definitions
"""
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod


def load_agent_definition(path: Path) -> dict:
    """Load a universal agent definition from YAML"""
    with open(path) as f:
        return yaml.safe_load(f)


class PlatformGenerator(ABC):
    """Base class for platform-specific generators"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier"""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return file extension for generated files"""
        pass

    @abstractmethod
    def generate(self, definition: dict) -> str:
        """Generate platform-specific content from universal definition"""
        pass

    def get_install_path(self, definition: dict) -> Path:
        """Get installation path for this platform"""
        platforms = definition.get("spec", {}).get("platforms", {})
        platform_config = platforms.get(self.platform_name, {})
        install_path = platform_config.get("install_path", f"~/.btr/agents/")
        return Path(install_path).expanduser()


class ClaudeCodeGenerator(PlatformGenerator):
    """Generate Claude Code agent format (Markdown with YAML frontmatter)"""

    @property
    def platform_name(self) -> str:
        return "claude_code"

    @property
    def file_extension(self) -> str:
        return ".md"

    def generate(self, definition: dict) -> str:
        metadata = definition.get("metadata", {})
        spec = definition.get("spec", {})
        platforms = spec.get("platforms", {})
        claude_config = platforms.get("claude_code", {})

        # Build frontmatter
        frontmatter = {
            "name": metadata.get("name"),
            "description": self._format_description(metadata),
            "model": claude_config.get("model", "sonnet"),
            "color": claude_config.get("color", "blue")
        }

        # Generate body content
        body = self._generate_body(definition)

        # Combine
        fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{fm_yaml}---\n\n{body}"

    def _format_description(self, metadata: dict) -> str:
        """Format description with trigger examples"""
        desc = metadata.get("description", "").strip()
        triggers = metadata.get("triggers", [])

        if triggers:
            examples = "\n\n".join([
                f"<example>\nuser: \"{t}\"\nassistant: \"I'll use this agent to help.\"\n</example>"
                for t in triggers[:3]
            ])
            return f"{desc}\n\nExamples:\n{examples}"
        return desc

    def _generate_body(self, definition: dict) -> str:
        """Generate the agent body instructions"""
        metadata = definition.get("metadata", {})
        spec = definition.get("spec", {})

        lines = [
            f"You are the {metadata.get('name')} agent for MCP-BTR.",
            "",
            "## Configuration",
            "",
            "Load environment from `~/.btr.env`:",
            "```bash",
            "source ~/.btr.env 2>/dev/null || true",
            "```",
            "",
            "## Execution Phases",
            ""
        ]

        # Add phases
        for phase in spec.get("phases", []):
            lines.append(f"### {phase.get('name', 'Phase').title()}")
            lines.append("")
            lines.append(phase.get("description", ""))
            lines.append("")

            for action in phase.get("actions", []):
                action_type = action.get("type")
                if action_type == "api_call":
                    lines.append("```bash")
                    method = action.get("method", "GET")
                    endpoint = action.get("endpoint", "")
                    if method == "GET":
                        lines.append(f'curl -s "{endpoint}"')
                    else:
                        body = action.get("body", {})
                        lines.append(f'curl -s -X {method} "{endpoint}" \\')
                        lines.append("  -H 'Content-Type: application/json' \\")
                        lines.append(f"  -d '{json.dumps(body)}'")
                    lines.append("```")
                elif action_type == "shell":
                    lines.append("```bash")
                    lines.append(action.get("command", ""))
                    lines.append("```")

            lines.append("")

        # Add decision rules if present
        decide_phase = next(
            (p for p in spec.get("phases", []) if p.get("name") == "decide"),
            None
        )
        if decide_phase:
            budget = decide_phase.get("budget", {})
            lines.append("## Tool Budget")
            lines.append("")
            lines.append(f"- Minimum: {budget.get('minimum', 5)} tools")
            lines.append(f"- Optimal: {budget.get('optimal', '15-30')} tools")
            lines.append(f"- Maximum: {budget.get('maximum', 40)} tools")
            lines.append("")

        return "\n".join(lines)


class CursorGenerator(PlatformGenerator):
    """Generate Cursor rules format"""

    @property
    def platform_name(self) -> str:
        return "cursor"

    @property
    def file_extension(self) -> str:
        return ".mdc"

    def generate(self, definition: dict) -> str:
        metadata = definition.get("metadata", {})
        spec = definition.get("spec", {})

        lines = [
            f"# {metadata.get('name')}",
            "",
            metadata.get("description", "").strip(),
            "",
            "## When to use this rule",
            "",
        ]

        for trigger in metadata.get("triggers", []):
            lines.append(f"- {trigger}")

        lines.extend([
            "",
            "## Instructions",
            "",
            "When this rule applies, execute the following steps:",
            ""
        ])

        for i, phase in enumerate(spec.get("phases", []), 1):
            lines.append(f"{i}. **{phase.get('name', 'Step').title()}**: {phase.get('description', '')}")

        lines.extend([
            "",
            "## API Endpoints",
            "",
            "Use these BTR API endpoints:",
            "",
            "- `GET /api/tools` - List all available tools",
            "- `GET /api/current` - List enabled tools",
            "- `POST /api/update` - Update enabled tools",
            "- `POST /api/presets/load` - Load a preset",
            ""
        ])

        return "\n".join(lines)


class GeminiGenerator(PlatformGenerator):
    """Generate Gemini agent format"""

    @property
    def platform_name(self) -> str:
        return "gemini"

    @property
    def file_extension(self) -> str:
        return ".md"

    def generate(self, definition: dict) -> str:
        # Gemini uses a similar format to Claude Code
        claude_gen = ClaudeCodeGenerator()
        content = claude_gen.generate(definition)

        # Modify frontmatter for Gemini
        metadata = definition.get("metadata", {})
        spec = definition.get("spec", {})
        platforms = spec.get("platforms", {})
        gemini_config = platforms.get("gemini", {})

        frontmatter = {
            "name": metadata.get("name"),
            "description": metadata.get("description", "").strip(),
            "model": gemini_config.get("model", "gemini-pro")
        }

        # Rebuild with Gemini frontmatter
        body_start = content.find("---", 4) + 4
        body = content[body_start:].strip()

        fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{fm_yaml}---\n\n{body}"


class OpenAIGenerator(PlatformGenerator):
    """Generate OpenAI function definitions"""

    @property
    def platform_name(self) -> str:
        return "openai"

    @property
    def file_extension(self) -> str:
        return ".json"

    def generate(self, definition: dict) -> str:
        metadata = definition.get("metadata", {})

        function_def = {
            "type": "function",
            "function": {
                "name": metadata.get("name", "").replace("-", "_"),
                "description": metadata.get("description", "").strip()[:1024],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project to analyze"
                        },
                        "preset": {
                            "type": "string",
                            "enum": ["minimal", "development", "research", "full"],
                            "description": "Optional preset to use"
                        }
                    },
                    "required": []
                }
            }
        }

        return json.dumps(function_def, indent=2)


class GenericScriptGenerator(PlatformGenerator):
    """Generate standalone bash script"""

    @property
    def platform_name(self) -> str:
        return "generic"

    @property
    def file_extension(self) -> str:
        return ".sh"

    def generate(self, definition: dict) -> str:
        metadata = definition.get("metadata", {})
        spec = definition.get("spec", {})

        lines = [
            "#!/bin/bash",
            f"# {metadata.get('name')} - BTR Agent Script",
            f"# {metadata.get('description', '').strip().split(chr(10))[0]}",
            "#",
            "# Usage: ./" + metadata.get("name", "agent") + ".sh [project_path]",
            "",
            "set -e",
            "",
            "# Load configuration",
            "if [ -f ~/.btr.env ]; then",
            "    source ~/.btr.env",
            "fi",
            "",
            "BTR_HOST=${BTR_HOST:-localhost}",
            "BTR_UI_PORT=${BTR_UI_PORT:-5010}",
            "BTR_API=\"http://${BTR_HOST}:${BTR_UI_PORT}\"",
            "",
            "PROJECT_PATH=${1:-.}",
            "cd \"$PROJECT_PATH\"",
            "",
        ]

        # Add phase implementations
        for phase in spec.get("phases", []):
            phase_name = phase.get("name", "phase")
            lines.append(f"# Phase: {phase_name}")
            lines.append(f"echo \"[{phase_name.upper()}] {phase.get('description', '')}\"")
            lines.append("")

            for action in phase.get("actions", []):
                action_type = action.get("type")
                if action_type == "api_call":
                    method = action.get("method", "GET")
                    endpoint = action.get("endpoint", "").replace(
                        "${BTR_HOST}", "${BTR_HOST}"
                    ).replace("${BTR_UI_PORT}", "${BTR_UI_PORT}")

                    if method == "GET":
                        output = action.get("output", "result")
                        lines.append(f'{output}=$(curl -s "{endpoint}")')
                    else:
                        body = action.get("body", {})
                        lines.append(f'curl -s -X {method} "{endpoint}" \\')
                        lines.append(f"  -H 'Content-Type: application/json' \\")
                        lines.append(f"  -d '{json.dumps(body)}'")

                elif action_type == "shell":
                    cmd = action.get("command", "")
                    output = action.get("output")
                    optional = action.get("optional", False)

                    if optional:
                        if output:
                            lines.append(f'{output}=$({cmd} 2>/dev/null || echo "")')
                        else:
                            lines.append(f"{cmd} 2>/dev/null || true")
                    else:
                        if output:
                            lines.append(f'{output}=$({cmd})')
                        else:
                            lines.append(cmd)

            lines.append("")

        lines.append('echo "Done."')

        return "\n".join(lines)


# Registry of all generators
GENERATORS: dict[str, type[PlatformGenerator]] = {
    "claude_code": ClaudeCodeGenerator,
    "cursor": CursorGenerator,
    "gemini": GeminiGenerator,
    "openai": OpenAIGenerator,
    "generic": GenericScriptGenerator,
}


def generate_for_platform(definition: dict, platform: str) -> str:
    """Generate agent content for a specific platform"""
    if platform not in GENERATORS:
        raise ValueError(f"Unknown platform: {platform}. Available: {list(GENERATORS.keys())}")

    generator = GENERATORS[platform]()
    return generator.generate(definition)


def generate_all(definition: dict) -> dict[str, str]:
    """Generate agent content for all platforms"""
    results = {}
    for platform, generator_cls in GENERATORS.items():
        try:
            generator = generator_cls()
            results[platform] = generator.generate(definition)
        except Exception as e:
            results[platform] = f"# Error generating for {platform}: {e}"
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generator.py <agent.yaml> [platform]")
        sys.exit(1)

    agent_path = Path(sys.argv[1])
    platform = sys.argv[2] if len(sys.argv) > 2 else None

    definition = load_agent_definition(agent_path)

    if platform:
        print(generate_for_platform(definition, platform))
    else:
        for p, content in generate_all(definition).items():
            print(f"\n{'='*60}")
            print(f"Platform: {p}")
            print('='*60)
            print(content)
