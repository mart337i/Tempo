import configparser
import os
from pathlib import Path
from typing import Any, Dict, Optional

import logging

_logger = logging.getLogger(__name__)


class TempoConfig:
    """Manages configuration with multiple sources and priority levels."""

    # Environment variable prefix for server settings
    ENV_PREFIX = "TEMPO_SERVER_"

    # Default configuration values
    DEFAULTS = {
        "server": {
            "name": "Tempo API",
            "host": "0.0.0.0",
            "port": "8000",
            "reload": "false",
            "workers": "1",
            "openapi_url": "/openapi.json",
            "docs_url": "/docs",
            "description": "Tempo API",
            "version": "0.1.0",
        },
        "database": {
            "url": "",
        },
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_file: Optional path to config file. Defaults to ./tempo.conf
        """
        self.config = configparser.ConfigParser()
        self.config.read_dict(self.DEFAULTS)

        # Determine config file path
        if config_file:
            self.config_file = Path(config_file)
        else:
            self.config_file = Path.cwd() / "tempo.conf"

        # Load from file if exists
        self._load_from_file()

        # Load from environment variables (for factory communication)
        self._load_from_env()

    def _load_from_file(self):
        """Load configuration from file if it exists."""
        if self.config_file.exists():
            try:
                self.config.read(self.config_file)
                _logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                _logger.warning(f"Failed to read config file {self.config_file}: {e}")
        else:
            _logger.debug(f"Config file {self.config_file} not found, using defaults")

    def _load_from_env(self):
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self.ENV_PREFIX):
                # Convert TEMPO_SERVER_NAME -> name
                setting_key = key[len(self.ENV_PREFIX) :].lower()
                self.config.set("server", setting_key, value)
                _logger.debug(f"Loaded {setting_key} from environment variable")

    def __getitem__(self, key: str) -> str:
        """Shortcut access: config["host"] or config["server.host"].

        Plain key (e.g. "host") is resolved by searching all sections.
        Raises KeyError if the key is missing or ambiguous across sections.
        """
        if "." in key:
            section, _, k = key.partition(".")
            value = self.get(section, k)
            if value is None:
                raise KeyError(key)
            return value

        # search all sections for the key
        matches = [
            (section, self.config.get(section, key))
            for section in self.config.sections()
            if self.config.has_option(section, key)
        ]
        if len(matches) == 0:
            raise KeyError(key)
        if len(matches) > 1:
            raise KeyError(
                f"Ambiguous key {key!r} found in sections: "
                + ", ".join(s for s, _ in matches)
                + " — use 'section.key' syntax"
            )
        return matches[0][1]

    def __repr__(self) -> str:
        sections = {}
        for section in self.config.sections():
            sections[section] = dict(self.config.items(section))
        return "\n".join(
            f"[{section}]\n" + "\n".join(f"  {k} = {v}" for k, v in items.items())
            for section, items in sections.items()
        )

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Config section (e.g., 'server')
            key: Config key (e.g., 'host')
            fallback: Default value if not found

        Returns:
            Configuration value
        """
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get a configuration value as integer."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get a configuration value as boolean."""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def update_from_args(self, args: Dict[str, Any]):
        """
        Update configuration from CLI arguments.

        Args:
            args: Dictionary of CLI arguments
        """
        if not self.config.has_section("server"):
            self.config.add_section("server")

        # Map of CLI arg names to config keys
        arg_mapping = {
            "name": "name",
            "host": "host",
            "port": "port",
            "reload": "reload",
            "workers": "workers",
        }

        for arg_name, config_key in arg_mapping.items():
            if arg_name in args and args[arg_name] is not None:
                value = str(args[arg_name])
                self.config.set("server", config_key, value)
                _logger.debug(f"Set {config_key}={value} from CLI argument")

    def export_to_env(self):
        """
        Export server configuration to environment variables.

        This is used to communicate configuration to the uvicorn factory.
        """
        if not self.config.has_section("server"):
            return

        for key, value in self.config.items("server"):
            env_key = f"{self.ENV_PREFIX}{key.upper()}"
            os.environ[env_key] = str(value)
            _logger.debug(f"Exported {env_key}={value}")

    def get_server_config(self) -> Dict[str, Any]:
        """
        Get server configuration as a dictionary.

        Returns:
            Dictionary with server configuration
        """
        return {
            "name": self.get("server", "name"),
            "host": self.get("server", "host"),
            "port": self.getint("server", "port"),
            "reload": self.getboolean("server", "reload"),
            "workers": self.getint("server", "workers"),
            "openapi_url": self.get("server", "openapi_url"),
            "docs_url": self.get("server", "docs_url"),
            "description": self.get("server", "description"),
            "version": self.get("server", "version"),
        }


# Global config instance (created when needed)
_config_instance: Optional[TempoConfig] = None


def get_config(config_file: Optional[str] = None) -> TempoConfig:
    """
    Get the global configuration instance.

    Args:
        config_file: Optional path to config file

    Returns:
        TempoConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TempoConfig(config_file=config_file)
    return _config_instance


def reset_config():
    """Reset the global configuration instance (mainly for testing)."""
    global _config_instance
    _config_instance = None
