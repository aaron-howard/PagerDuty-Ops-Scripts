"""
PagerDuty Configuration Module

Configuration management for PagerDuty API interactions.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError

# Set up logging
logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for PagerDuty settings."""

    DEFAULT_CONFIG_FILES = [
        ".pagerduty.yaml",
        ".pagerduty.yml",
        ".pagerduty.json",
        "pagerduty.yaml",
        "pagerduty.yml",
        "pagerduty.json",
    ]

    def __init__(self, config_file: str | None = None, env_prefix: str = "PD"):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file (optional)
            env_prefix: Prefix for environment variables (default: "PD")
        """
        self.config_file = config_file
        self.env_prefix = env_prefix.upper()
        self._config: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """Load configuration from file and environment variables."""
        if self._loaded:
            return

        # Load from file if specified
        if self.config_file:
            self._load_from_file(self.config_file)
        else:
            # Try default config files
            for default_file in self.DEFAULT_CONFIG_FILES:
                if os.path.exists(default_file):
                    self._load_from_file(default_file)
                    break

        # Override with environment variables
        self._load_from_environment()

        self._loaded = True
        logger.debug(f"Configuration loaded from {len(self._config)} sources")

    def _load_from_file(self, config_path: str) -> None:
        """Load configuration from file."""
        try:
            path = Path(config_path)
            if not path.exists():
                raise ConfigError(f"Config file not found: {config_path}")

            with open(config_path, encoding="utf-8") as f:
                if path.suffix in (".yaml", ".yml"):
                    self._config = yaml.safe_load(f) or {}
                elif path.suffix == ".json":
                    self._config = json.load(f)
                else:
                    raise ConfigError(f"Unsupported config file format: {config_path}")

            logger.info(f"Loaded configuration from {config_path}")

        except Exception as e:
            raise ConfigError(f"Failed to load config from {config_path}: {str(e)}") from e

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_config = {}

        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.env_prefix) :].lower()
                if config_key.startswith("_"):
                    config_key = config_key[1:]

                # Replace underscores with dots for nested config
                config_key = config_key.replace("_", ".")

                # Convert value type
                env_config[config_key] = self._convert_env_value(value)

        # Merge environment config with file config (env takes precedence)
        self._deep_merge(self._config, env_config)

        if env_config:
            logger.info(f"Loaded {len(env_config)} configuration values from environment")

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable value to appropriate type."""
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        elif value.lower() in ("false", "no", "off", "0"):
            return False
        elif value.isdigit():
            return int(value)
        elif value.replace(".", "", 1).isdigit() and "." in value:
            return float(value)
        elif value.lower() in ("null", "none", ""):
            return None
        else:
            return value

    def _deep_merge(self, target: dict, source: dict) -> None:
        """Deep merge source dictionary into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        if not self._loaded:
            self.load()

        # Support dot notation for nested keys
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        if not self._loaded:
            self.load()

        keys = key.split(".")
        current = self._config

        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        # Set the final value
        current[keys[-1]] = value

    def validate(self, required_keys: list | None = None) -> bool:
        """
        Validate configuration.

        Args:
            required_keys: List of required configuration keys

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self._loaded:
            self.load()

        if required_keys:
            missing = [key for key in required_keys if not self.get(key)]
            if missing:
                raise ConfigError(f"Missing required configuration keys: {', '.join(missing)}")

        return True

    def to_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary."""
        if not self._loaded:
            self.load()
        return self._config.copy()


def load_config(config_file: str | None = None) -> Config:
    """
    Load and return configuration.

    Args:
        config_file: Path to configuration file (optional)

    Returns:
        Configured Config instance
    """
    cfg = Config(config_file)
    cfg.load()
    return cfg


# Lazy process-wide defaults (no disk/env read until first use).
_default_singleton: Config | None = None
_override_config_file: str | None = None


def configure_default_config_file(config_file: str | None) -> None:
    """
    Set the config file path used by get_config() / the module-level `config` proxy.

    Resets the cached singleton so the next access loads fresh. Call before any API
    client uses default config, typically right after parsing ``--config``.
    """
    global _default_singleton, _override_config_file
    _override_config_file = config_file
    _default_singleton = None


def get_config() -> Config:
    """Return the process-wide default Config, loading it on first access."""
    global _default_singleton
    if _default_singleton is None:
        _default_singleton = Config(config_file=_override_config_file)
        _default_singleton.load()
    return _default_singleton


def reset_default_config_for_testing() -> None:
    """Clear cached default config (tests only)."""
    global _default_singleton, _override_config_file
    _default_singleton = None
    _override_config_file = None


class _LazyConfigProxy:
    """Forwards to get_config() so ``from pagerduty.config import config`` stays lazy."""

    __slots__ = ()

    def get(self, key: str, default: Any = None) -> Any:
        return get_config().get(key, default)

    def set(self, key: str, value: Any) -> None:
        get_config().set(key, value)

    def load(self) -> None:
        get_config().load()

    def validate(self, required_keys: list | None = None) -> bool:
        return get_config().validate(required_keys)

    def to_dict(self) -> dict[str, Any]:
        return get_config().to_dict()


config = _LazyConfigProxy()
