# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Unit tests for utility functions in spdx_verify module.
"""

import os
from pathlib import Path
from unittest.mock import patch, mock_open

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import (
    load_config,
    is_github_actions,
    set_github_output,
    Colors,
    DEFAULT_LICENSE,
    DEFAULT_COPYRIGHT,
    CONFIG_FILE,
)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_default_constants(self):
        """Test that default constants are properly defined."""
        assert DEFAULT_LICENSE == "Apache-2.0"
        assert DEFAULT_COPYRIGHT == "The Linux Foundation"
        assert CONFIG_FILE == "spdx-config.yaml"

    def test_colors_class(self):
        """Test Colors class has required attributes."""
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "YELLOW")
        assert hasattr(Colors, "BLUE")
        assert hasattr(Colors, "END")
        assert hasattr(Colors, "BOLD")

    def test_load_config_success(self):
        """Test successful config loading."""
        config = load_config()

        # Should be a dictionary
        assert isinstance(config, dict)

        # Should contain required sections
        assert "languages" in config
        assert "default_skip_patterns" in config

        # Should have language configurations
        assert isinstance(config["languages"], dict)
        assert len(config["languages"]) > 0

        # Should have default skip patterns
        assert isinstance(config["default_skip_patterns"], list)

    def test_load_config_missing_file(self):
        """Test config loading when file is missing."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            config = load_config()

            # Should return default config structure
            assert isinstance(config, dict)
            assert "languages" in config
            assert "default_skip_patterns" in config

    def test_load_config_invalid_yaml(self):
        """Test config loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            config = load_config()

            # Should return default config structure on error
            assert isinstance(config, dict)
            assert "languages" in config

    def test_is_github_actions_true(self):
        """Test GitHub Actions detection when running in GHA."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert is_github_actions() is True

    def test_is_github_actions_false(self):
        """Test GitHub Actions detection when not in GHA."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_github_actions() is False

    def test_is_github_actions_false_value(self):
        """Test GitHub Actions detection with false value."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            assert is_github_actions() is False

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_OUTPUT": "/tmp/output"})
    def test_set_github_output_success(self):
        """Test setting GitHub Actions output."""
        with patch("builtins.open", mock_open()) as mock_file:
            set_github_output("test_key", "test_value")

            # Should open the output file
            mock_file.assert_called_once_with("/tmp/output", "a", encoding="utf-8")

            # Should write the key=value pair
            handle = mock_file.return_value
            handle.write.assert_called_once_with("test_key=test_value\n")

    def test_set_github_output_no_env(self):
        """Test setting GitHub Actions output when GITHUB_OUTPUT not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an exception
            set_github_output("test_key", "test_value")

    @patch("builtins.open", side_effect=IOError("Write error"))
    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_OUTPUT": "/tmp/output"})
    def test_set_github_output_write_error(self, mock_open):
        """Test handling write errors in GitHub Actions output."""
        # Should not raise an exception even on write errors
        set_github_output("test_key", "test_value")


class TestConfigValidation:
    """Test configuration file validation."""

    def test_config_structure_languages(self):
        """Test that config has proper language structure."""
        config = load_config()
        languages = config.get("languages", {})

        for lang_name, lang_config in languages.items():
            assert isinstance(lang_name, str), (
                f"Language name should be string: {lang_name}"
            )
            assert isinstance(lang_config, dict), (
                f"Language config should be dict: {lang_name}"
            )

            # Should have either extensions or filenames
            has_extensions = "extensions" in lang_config
            has_filenames = "filenames" in lang_config
            assert has_extensions or has_filenames, (
                f"Language {lang_name} should have extensions or filenames"
            )

            # Should have comment_prefix
            assert "comment_prefix" in lang_config, (
                f"Language {lang_name} should have comment_prefix"
            )
            assert isinstance(lang_config["comment_prefix"], str)

    def test_config_structure_skip_patterns(self):
        """Test that config has proper skip patterns structure."""
        config = load_config()
        skip_patterns = config.get("default_skip_patterns", [])

        assert isinstance(skip_patterns, list)
        for pattern in skip_patterns:
            assert isinstance(pattern, str), f"Skip pattern should be string: {pattern}"

    def test_config_python_language(self):
        """Test Python language configuration."""
        config = load_config()
        python_config = config["languages"].get("python")

        assert python_config is not None
        assert python_config["comment_prefix"] == "#"
        assert ".py" in python_config["extensions"]

    def test_config_javascript_language(self):
        """Test JavaScript language configuration."""
        config = load_config()
        js_config = config["languages"].get("javascript")

        assert js_config is not None
        assert js_config["comment_prefix"] == "//"
        assert ".js" in js_config["extensions"]

    def test_config_essential_skip_patterns(self):
        """Test that essential skip patterns are present."""
        config = load_config()
        skip_patterns = config.get("default_skip_patterns", [])

        # Convert to string for easier checking
        # patterns_str = " ".join(skip_patterns)  # Unused

        # Should have common cache/build directories
        essential_patterns = [
            "__pycache__",
            "node_modules",
            ".git",
        ]

        for pattern in essential_patterns:
            assert any(pattern in p for p in skip_patterns), (
                f"Should have pattern containing '{pattern}'"
            )


class TestConfigFileHandling:
    """Test configuration file handling edge cases."""

    def test_config_with_empty_file(self):
        """Test handling empty config file."""
        with patch("builtins.open", mock_open(read_data="")):
            config = load_config()

            # Should handle empty file gracefully
            assert isinstance(config, dict)

    def test_config_with_minimal_content(self):
        """Test handling minimal valid config."""
        minimal_yaml = """
languages: {}
default_skip_patterns: []
"""
        with patch("builtins.open", mock_open(read_data=minimal_yaml)):
            config = load_config()

            assert config["languages"] == {}
            assert config["default_skip_patterns"] == []

    def test_config_with_comments_only(self):
        """Test handling config file with only comments."""
        comments_yaml = """
# This is a comment
# Another comment
"""
        with patch("builtins.open", mock_open(read_data=comments_yaml)):
            config = load_config()

            # Should handle comments-only file
            assert isinstance(config, dict)

    def test_config_missing_languages_section(self):
        """Test handling config without languages section."""
        no_languages_yaml = """
default_skip_patterns:
  - "*.pyc"
"""
        with patch("builtins.open", mock_open(read_data=no_languages_yaml)):
            config = load_config()

            # Should provide default languages section
            assert "languages" in config
            assert isinstance(config["languages"], dict)

    def test_config_missing_skip_patterns_section(self):
        """Test handling config without skip patterns section."""
        no_skip_yaml = """
languages:
  python:
    comment_prefix: "#"
    extensions: [".py"]
"""
        with patch("builtins.open", mock_open(read_data=no_skip_yaml)):
            config = load_config()

            # Should provide default skip patterns section
            assert "default_skip_patterns" in config
            assert isinstance(config["default_skip_patterns"], list)

    @patch("yaml.safe_load", side_effect=Exception("YAML parse error"))
    def test_config_yaml_parse_error(self, mock_yaml):
        """Test handling YAML parsing errors."""
        with patch("builtins.open", mock_open(read_data="some content")):
            config = load_config()

            # Should return default config on parse error
            assert isinstance(config, dict)
            assert "languages" in config
            assert "default_skip_patterns" in config

    def test_config_permission_error(self):
        """Test handling permission errors when reading config."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            config = load_config()

            # Should return default config on permission error
            assert isinstance(config, dict)
            assert "languages" in config
            assert "default_skip_patterns" in config
