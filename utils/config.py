"""
Configuration loader for UnlockEgypt Parser.

Loads settings from config.yaml and provides typed access to configuration values.
"""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """
    Singleton configuration loader.

    Loads config.yaml once and provides access to all settings.
    """

    _instance = None
    _config: dict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from config.yaml."""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested configuration value.

        Args:
            *keys: Path to the config value (e.g., 'browser', 'headless')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    # Convenience properties for common settings
    @property
    def base_url(self) -> str:
        return self.get("website", "base_url", default="https://egymonuments.gov.eg")

    @property
    def page_types(self) -> list[str]:
        return self.get("website", "page_types", default=[])

    @property
    def headless(self) -> bool:
        return self.get("browser", "headless", default=True)

    @property
    def window_size(self) -> tuple[int, int]:
        width = self.get("browser", "window_width", default=1920)
        height = self.get("browser", "window_height", default=1080)
        return (width, height)

    @property
    def user_agent(self) -> str:
        return self.get("browser", "user_agent",
                       default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    @property
    def implicit_wait(self) -> int:
        return self.get("timing", "implicit_wait_timeout", default=10)

    @property
    def page_load_wait(self) -> float:
        return self.get("timing", "page_load_wait", default=5)

    @property
    def scroll_wait(self) -> float:
        return self.get("timing", "scroll_wait", default=2)

    @property
    def show_more_wait(self) -> float:
        return self.get("timing", "show_more_wait", default=3)

    @property
    def http_timeout(self) -> int:
        return self.get("timing", "http_timeout", default=15)

    @property
    def geocoding_rate_limit(self) -> float:
        return self.get("timing", "geocoding_rate_limit", default=1.0)

    @property
    def nominatim_user_agent(self) -> str:
        return self.get("geocoding", "user_agent",
                       default="UnlockEgyptParser/3.2 (educational project)")


# Global config instance
config = Config()
