"""
Configuration loader for UnlockEgypt Parser.

Loads settings from config.yaml and provides typed access to configuration values.
"""

from pathlib import Path
from typing import Any, cast

import yaml


class Config:
    """
    Singleton configuration loader.

    Loads config.yaml once and provides access to all settings.
    """

    _instance: "Config | None" = None
    _config: dict[str, Any] | None = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.yaml."""
        # Find project root by looking for pyproject.toml
        config_path = self._find_project_root() / "config.yaml"
        with open(config_path, encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    @staticmethod
    def _find_project_root() -> Path:
        """Find project root by searching for pyproject.toml."""
        current = Path(__file__).resolve().parent
        for _ in range(10):  # Prevent infinite loop
            if (current / "pyproject.toml").exists():
                return current
            if current.parent == current:
                break
            current = current.parent
        # Fallback: assume standard src layout (4 levels up from utils/config.py)
        return Path(__file__).resolve().parent.parent.parent.parent

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
        result = self.get("website", "base_url", default="https://egymonuments.gov.eg")
        return cast(str, result)

    @property
    def page_types(self) -> list[str]:
        result = self.get("website", "page_types", default=[])
        return cast(list[str], result)

    @property
    def headless(self) -> bool:
        result = self.get("browser", "headless", default=True)
        return cast(bool, result)

    @property
    def window_size(self) -> tuple[int, int]:
        width = self.get("browser", "window_width", default=1920)
        height = self.get("browser", "window_height", default=1080)
        return (cast(int, width), cast(int, height))

    @property
    def user_agent(self) -> str:
        result = self.get(
            "browser",
            "user_agent",
            default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        return cast(str, result)

    @property
    def implicit_wait(self) -> int:
        result = self.get("timing", "implicit_wait_timeout", default=10)
        return cast(int, result)

    @property
    def page_load_wait(self) -> float:
        result = self.get("timing", "page_load_wait", default=5)
        return cast(float, result)

    @property
    def scroll_wait(self) -> float:
        result = self.get("timing", "scroll_wait", default=2)
        return cast(float, result)

    @property
    def show_more_wait(self) -> float:
        result = self.get("timing", "show_more_wait", default=3)
        return cast(float, result)

    @property
    def http_timeout(self) -> int:
        result = self.get("timing", "http_timeout", default=15)
        return cast(int, result)

    @property
    def geocoding_rate_limit(self) -> float:
        result = self.get("timing", "geocoding_rate_limit", default=1.0)
        return cast(float, result)

    @property
    def nominatim_user_agent(self) -> str:
        result = self.get(
            "geocoding",
            "user_agent",
            default="UnlockEgyptParser/3.4 (educational project)",
        )
        return cast(str, result)


# Global config instance
config = Config()
