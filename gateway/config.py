"""
BTR Gateway Configuration
"""
import os
import json
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Server
    host: str = "0.0.0.0"
    port: int = 8090
    log_level: str = "INFO"

    # Paths
    presets_dir: Path = Path("/app/presets")
    servers_dir: Path = Path("/app/servers")
    data_dir: Path = Path("/app/data")

    # Default preset
    default_preset: str = "development"

    class Config:
        env_prefix = "BTR_"


settings = Settings()


class ToolState:
    """Manages the current state of enabled tools"""

    def __init__(self):
        self.enabled_tools: set[str] = set()
        self.state_file = settings.data_dir / "enabled_tools.json"
        self._load_state()

    def _load_state(self):
        """Load enabled tools from persistent storage"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.enabled_tools = set(data.get("enabled_tools", []))
            except (json.JSONDecodeError, IOError):
                self._load_default_preset()
        else:
            self._load_default_preset()

    def _load_default_preset(self):
        """Load the default preset"""
        preset_file = settings.presets_dir / f"{settings.default_preset}.json"
        if preset_file.exists():
            try:
                with open(preset_file) as f:
                    data = json.load(f)
                    self.enabled_tools = set(data.get("tools", []))
            except (json.JSONDecodeError, IOError):
                self.enabled_tools = set()

    def save_state(self):
        """Save enabled tools to persistent storage"""
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump({"enabled_tools": list(self.enabled_tools)}, f, indent=2)

    def enable_tool(self, tool: str):
        """Enable a specific tool"""
        self.enabled_tools.add(tool)
        self.save_state()

    def disable_tool(self, tool: str):
        """Disable a specific tool"""
        self.enabled_tools.discard(tool)
        self.save_state()

    def set_tools(self, tools: list[str]):
        """Replace all enabled tools"""
        self.enabled_tools = set(tools)
        self.save_state()

    def is_enabled(self, tool: str) -> bool:
        """Check if a tool is enabled"""
        return tool in self.enabled_tools

    def get_enabled(self) -> list[str]:
        """Get list of enabled tools"""
        return sorted(self.enabled_tools)


# Global tool state
tool_state = ToolState()
