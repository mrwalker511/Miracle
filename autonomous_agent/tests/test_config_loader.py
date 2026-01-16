"""Tests for configuration loader."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config_loader import ConfigLoader


class TestConfigLoader:
    """Test cases for ConfigLoader."""

    def test_initialization(self):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader()
        assert loader.config_dir == Path("config")

    def test_initialization_with_custom_dir(self):
        """Test ConfigLoader with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(tmpdir)
            assert loader.config_dir == Path(tmpdir)

    def test_load_yaml_file_not_found(self):
        """Test loading non-existent YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(tmpdir)
            with pytest.raises(FileNotFoundError):
                loader.load_yaml("nonexistent.yaml")

    def test_load_yaml_valid(self):
        """Test loading valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text(
                "key1: value1\n"
                "key2:\n"
                "  nested: value2\n",
                encoding="utf-8"
            )

            loader = ConfigLoader(tmpdir)
            config = loader.load_yaml("test.yaml")

            assert config["key1"] == "value1"
            assert config["key2"]["nested"] == "value2"

    def test_env_var_substitution(self):
        """Test environment variable substitution."""
        os.environ["TEST_VAR"] = "test_value"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("key: ${TEST_VAR}", encoding="utf-8")

            loader = ConfigLoader(tmpdir)
            config = loader.load_yaml("test.yaml")

            assert config["key"] == "test_value"

        del os.environ["TEST_VAR"]

    def test_env_var_substitution_with_default(self):
        """Test environment variable substitution with default value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("key: ${NONEXISTENT_VAR:default}", encoding="utf-8")

            loader = ConfigLoader(tmpdir)
            config = loader.load_yaml("test.yaml")

            assert config["key"] == "default"

    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text(
                "level1:\n"
                "  level2:\n"
                "    value: test\n",
                encoding="utf-8"
            )

            loader = ConfigLoader(tmpdir)
            value = loader.get("test", "level1", "level2", "value")

            assert value == "test"

    def test_get_with_default(self):
        """Test getting configuration value with default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("key: value", encoding="utf-8")

            loader = ConfigLoader(tmpdir)
            value = loader.get("test", "nonexistent", default="default_value")

            assert value == "default_value"

    def test_substitute_in_dict(self):
        """Test environment variable substitution in dict."""
        os.environ["DICT_KEY"] = "dict_value"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text(
                "nested:\n"
                "  key: ${DICT_KEY}\n",
                encoding="utf-8"
            )

            loader = ConfigLoader(tmpdir)
            config = loader.load_yaml("test.yaml")

            assert config["nested"]["key"] == "dict_value"

        del os.environ["DICT_KEY"]

    def test_substitute_in_list(self):
        """Test environment variable substitution in list."""
        os.environ["LIST_ITEM"] = "list_value"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text(
                "items:\n"
                "  - ${LIST_ITEM}\n"
                "  - static\n",
                encoding="utf-8"
            )

            loader = ConfigLoader(tmpdir)
            config = loader.load_yaml("test.yaml")

            assert config["items"][0] == "list_value"
            assert config["items"][1] == "static"

        del os.environ["LIST_ITEM"]
