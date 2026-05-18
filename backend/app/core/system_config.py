import json
import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

# Always resolve relative to this file's directory (backend/app/core/ → backend/)
CONFIG_FILE = str(Path(__file__).resolve().parent.parent.parent / "config.json")

class SystemSettings(BaseModel):
    """
    Application-wide settings for LLM and TTS providers.
    """
    llm_provider: Literal["claude", "local"] = Field(
        "claude",
        description="Which LLM provider to use: 'claude' (Anthropic API) or 'local' (HuggingFace)."
    )
    claude_model: str = Field(
        "claude-haiku-4-5",
        description="Claude model ID when llm_provider is 'claude'."
    )
    anthropic_api_key: str = Field(
        "",
        description="Anthropic API key for Claude API access."
    )
    llm_model_id: str = Field(
        "Qwen/Qwen3-8B",
        description="HuggingFace model ID when llm_provider is 'local'."
    )

    tts_provider: Literal["qwen3-local", "openai"] = Field("qwen3-local", description="The TTS provider.")
    tts_model: str = Field("qwen3-tts", description="The TTS model name.")

class ConfigManager:
    _instance = None
    _settings: SystemSettings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Loads config from file or creates default. Env var ANTHROPIC_API_KEY overrides empty config value."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self._settings = SystemSettings(**data)
            except Exception as e:
                print(f"Error loading config, using defaults: {e}")
                self._settings = SystemSettings()
        else:
            self._settings = SystemSettings()
            self.save_config()
        # Fall back to env var if config has no key (survives config resets)
        if not self._settings.anthropic_api_key:
            env_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if env_key:
                self._settings = self._settings.model_copy(update={"anthropic_api_key": env_key})

    def save_config(self):
        """Saves current config to file."""
        if self._settings:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(self._settings.model_dump_json(indent=2))

    def get_settings(self) -> SystemSettings:
        return self._settings

    def update_settings(self, new_settings: SystemSettings):
        self._settings = new_settings
        self.save_config()

# Global instance
config_manager = ConfigManager()
