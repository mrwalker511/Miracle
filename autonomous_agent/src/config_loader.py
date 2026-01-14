"""Configuration loader for YAML config files with environment variable substitution."""

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages configuration from YAML files."""

    def __init__(self, config_dir: str = "config"):
        """Initialize the config loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        load_dotenv()  # Load environment variables from .env file

    def _substitute_env_vars(self, value: Any) -> Any:
        """Recursively substitute environment variables in config values.

        Args:
            value: Configuration value (string, dict, list, etc.)

        Returns:
            Value with environment variables substituted
        """
        if isinstance(value, str):
            # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
            pattern = r'\$\{([^:}]+)(?::([^}]+))?\}'

            def replace_env(match):
                var_name = match.group(1)
                default_value = match.group(2)
                return os.getenv(var_name, default_value or '')

            return re.sub(pattern, replace_env, value)

        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]

        return value

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load and parse a YAML configuration file.

        Args:
            filename: Name of the YAML file (e.g., 'settings.yaml')

        Returns:
            Dictionary containing configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        file_path = self.config_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Substitute environment variables
        config = self._substitute_env_vars(config)

        return config

    def load_all_configs(self) -> Dict[str, Any]:
        """Load all configuration files.

        Returns:
            Dictionary with all configurations:
            {
                'settings': {...},
                'database': {...},
                'openai': {...},
                'prompts': {...},
                'safety': {...}
            }
        """
        configs = {}

        config_files = {
            'settings': 'settings.yaml',
            'database': 'database.yaml',
            'openai': 'openai.yaml',
            'prompts': 'system_prompts.yaml',
            'safety': 'safety_rules.yaml'
        }

        for key, filename in config_files.items():
            try:
                configs[key] = self.load_yaml(filename)
            except FileNotFoundError:
                print(f"Warning: Configuration file {filename} not found, using defaults")
                configs[key] = {}

        return configs

    def get(self, config_name: str, *keys: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation.

        Args:
            config_name: Name of config file (e.g., 'settings', 'database')
            *keys: Nested keys to traverse (e.g., 'system', 'name')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            loader.get('settings', 'system', 'version')  # Returns "0.1.0"
        """
        config = self.load_yaml(f"{config_name}.yaml")

        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# Singleton instance
_config_loader = None


def get_config_loader(config_dir: str = "config") -> ConfigLoader:
    """Get or create the singleton ConfigLoader instance.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader
