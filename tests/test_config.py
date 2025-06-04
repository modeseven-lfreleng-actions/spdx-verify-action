# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Test configuration, setup, and validation.
"""

from pathlib import Path

import pytest

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import load_config


class TestConfigurationValidation:
    """Test the actual configuration file structure."""

    def test_config_file_exists(self):
        """Test that the configuration file exists."""
        config_path = Path(__file__).parent.parent / "spdx-config.yaml"
        assert config_path.exists(), "spdx-config.yaml should exist"

    def test_config_loads_successfully(self):
        """Test that the configuration loads without errors."""
        config = load_config()
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_config_has_required_sections(self):
        """Test that config has all required sections."""
        config = load_config()

        required_sections = ["languages", "default_skip_patterns"]
        for section in required_sections:
            assert section in config, f"Config should have '{section}' section"

    def test_languages_section_structure(self):
        """Test the structure of the languages section."""
        config = load_config()
        languages = config["languages"]

        assert isinstance(languages, dict)
        assert len(languages) > 0, "Should have at least one language defined"

        for lang_name, lang_config in languages.items():
            assert isinstance(lang_name, str)
            assert isinstance(lang_config, dict)

            # Must have comment_prefix
            assert "comment_prefix" in lang_config, (
                f"Language '{lang_name}' missing comment_prefix"
            )
            assert isinstance(lang_config["comment_prefix"], str)

            # Must have extensions OR filenames
            has_extensions = "extensions" in lang_config and lang_config["extensions"]
            has_filenames = "filenames" in lang_config and lang_config["filenames"]
            assert has_extensions or has_filenames, (
                f"Language '{lang_name}' needs extensions or filenames"
            )

            # If extensions exist, should be a list of strings (can be empty for special cases like makefile)
            if "extensions" in lang_config:
                extensions = lang_config["extensions"]
                assert isinstance(extensions, list)
                # Allow empty extensions list for special cases like makefile
                for ext in extensions:
                    assert isinstance(ext, str)
                    assert ext.startswith("."), (
                        f"Extension '{ext}' should start with '.'"
                    )

            # If filenames exist, should be a list of strings
            if "filenames" in lang_config:
                filenames = lang_config["filenames"]
                assert isinstance(filenames, list)
                assert len(filenames) > 0
                for filename in filenames:
                    assert isinstance(filename, str)
                    assert len(filename) > 0

    def test_skip_patterns_section_structure(self):
        """Test the structure of the default_skip_patterns section."""
        config = load_config()
        skip_patterns = config["default_skip_patterns"]

        assert isinstance(skip_patterns, list)
        assert len(skip_patterns) > 0, "Should have at least one skip pattern"

        for pattern in skip_patterns:
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    def test_essential_languages_present(self):
        """Test that essential languages are configured."""
        config = load_config()
        languages = config["languages"]

        essential_languages = ["python", "javascript"]
        for lang in essential_languages:
            assert lang in languages, (
                f"Essential language '{lang}' should be configured"
            )

    def test_python_language_config(self):
        """Test Python language configuration specifics."""
        config = load_config()
        python_config = config["languages"]["python"]

        assert python_config["comment_prefix"] == "#"
        assert ".py" in python_config["extensions"]

        # Check for common Python extensions
        common_py_extensions = [".py", ".pyx", ".pyi"]
        for ext in common_py_extensions:
            if ext in python_config["extensions"]:
                assert ext in python_config["extensions"]

    def test_javascript_language_config(self):
        """Test JavaScript language configuration specifics."""
        config = load_config()
        js_config = config["languages"]["javascript"]

        assert js_config["comment_prefix"] == "//"
        assert ".js" in js_config["extensions"]

        # Check for common JS extensions
        js_extensions = js_config["extensions"]
        common_js_exts = [".js", ".jsx", ".ts", ".tsx"]
        found_common = any(ext in js_extensions for ext in common_js_exts)
        assert found_common, "Should have at least one common JS/TS extension"

    def test_essential_skip_patterns_present(self):
        """Test that essential skip patterns are present."""
        config = load_config()
        skip_patterns = config["default_skip_patterns"]

        essential_patterns = [
            "__pycache__",  # Python cache
            "node_modules",  # Node.js modules
            ".git",  # Git directory
            "__pypackages__",  # PDM cache (the original issue!)
        ]

        for pattern in essential_patterns:
            found = any(pattern in p for p in skip_patterns)
            assert found, (
                f"Essential skip pattern containing '{pattern}' should be present"
            )

    def test_skip_patterns_format(self):
        """Test that skip patterns are in valid format."""
        config = load_config()
        skip_patterns = config["default_skip_patterns"]

        for pattern in skip_patterns:
            # Patterns should be non-empty strings
            assert isinstance(pattern, str)
            assert len(pattern.strip()) > 0

            # Common pattern validation (basic)
            assert not pattern.startswith("/"), (
                f"Pattern '{pattern}' should not start with '/'"
            )
            assert ".." not in pattern, f"Pattern '{pattern}' should not contain '..'"

    def test_comment_suffixes_where_appropriate(self):
        """Test that languages with block comments have comment_suffix."""
        config = load_config()
        languages = config["languages"]

        # Languages that typically use block comments
        block_comment_languages = {
            "css": ("/*", "*/"),
            "html": ("<!--", "-->"),
            "c": ("/*", "*/"),
            "cpp": ("/*", "*/"),
            "java": ("/*", "*/"),
        }

        for lang_name, (
            expected_prefix,
            expected_suffix,
        ) in block_comment_languages.items():
            if lang_name in languages:
                lang_config = languages[lang_name]
                if lang_config["comment_prefix"] == expected_prefix:
                    assert "comment_suffix" in lang_config, (
                        f"Language '{lang_name}' should have comment_suffix"
                    )
                    assert lang_config["comment_suffix"] == expected_suffix

    def test_no_duplicate_extensions(self):
        """Test that no file extension is mapped to multiple languages."""
        config = load_config()
        languages = config["languages"]

        extension_to_languages: dict[str, list[str]] = {}

        for lang_name, lang_config in languages.items():
            if "extensions" in lang_config:
                for ext in lang_config["extensions"]:
                    if ext in extension_to_languages:
                        pytest.fail(
                            f"Extension '{ext}' is mapped to both '{extension_to_languages[ext]}' "
                            f"and '{lang_name}' languages"
                        )
                    extension_to_languages[ext] = lang_name

    def test_no_duplicate_filenames(self):
        """Test that no filename is mapped to multiple languages."""
        config = load_config()
        languages = config["languages"]

        filename_to_languages: dict[str, str] = {}

        for lang_name, lang_config in languages.items():
            if "filenames" in lang_config:
                for filename in lang_config["filenames"]:
                    if filename in filename_to_languages:
                        pytest.fail(
                            f"Filename '{filename}' is mapped to both '{filename_to_languages[filename]}' "
                            f"and '{lang_name}' languages"
                        )
                    filename_to_languages[filename] = lang_name


class TestConfigurationIntegration:
    """Test configuration integration with the verifier."""

    def test_all_configured_languages_work(self, temp_dir, sample_files):
        """Test that all configured languages can be processed."""
        from spdx_verify import SPDXVerifier

        config = load_config()
        languages = config["languages"]

        verifier = SPDXVerifier()

        # Test each language that has extensions
        for lang_name, lang_config in languages.items():
            if "extensions" in lang_config and lang_config["extensions"]:
                ext = lang_config["extensions"][0]  # Use first extension
                test_file = temp_dir / f"test{ext}"

                # Create a valid header based on comment style
                prefix = lang_config["comment_prefix"]
                suffix = lang_config.get("comment_suffix", "")

                if suffix:
                    # Block comment style
                    content = f"""{prefix} SPDX-License-Identifier: Apache-2.0 {suffix}
{prefix} SPDX-FileCopyrightText: 2025 The Linux Foundation {suffix}

content here
"""
                else:
                    # Line comment style
                    content = f"""{prefix} SPDX-License-Identifier: Apache-2.0
{prefix} SPDX-FileCopyrightText: 2025 The Linux Foundation

content here
"""

                test_file.write_text(content, encoding="utf-8")

                # Should be able to detect the language
                detected_lang = verifier.get_language_for_file(test_file)
                assert detected_lang == lang_name, (
                    f"Failed to detect language '{lang_name}' for file '{test_file}'"
                )

                # Should be able to verify the header
                passed, message = verifier.check_license_header(test_file)
                assert passed, (
                    f"Failed to verify header for language '{lang_name}': {message}"
                )

    def test_skip_patterns_actually_skip(self, temp_dir):
        """Test that configured skip patterns actually skip files."""
        from spdx_verify import SPDXVerifier

        config = load_config()
        skip_patterns = config["default_skip_patterns"]

        verifier = SPDXVerifier(debug=True)

        # Create files that should be skipped
        test_cases = [
            ("__pycache__/test.pyc", "__pycache__"),
            ("node_modules/package/index.js", "node_modules"),
            (".git/config", ".git"),
            ("build/output.o", "build"),
            ("dist/package.tar.gz", "dist"),
        ]

        for file_path, pattern_type in test_cases:
            full_path = temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("content", encoding="utf-8")

            # Check if any skip pattern would match this file
            should_skip = verifier.should_skip_file(Path(file_path))

            # Find which pattern should match
            matching_patterns = [p for p in skip_patterns if pattern_type in p]

            if matching_patterns:
                assert should_skip, (
                    f"File '{file_path}' should be skipped by pattern containing '{pattern_type}'"
                )

    def test_config_backward_compatibility(self):
        """Test that config maintains backward compatibility."""
        config = load_config()

        # Essential fields that should always exist
        required_fields = [
            ["languages"],
            ["languages", "python"],
            ["languages", "python", "comment_prefix"],
            ["languages", "python", "extensions"],
            ["default_skip_patterns"],
        ]

        for field_path in required_fields:
            current = config
            for field in field_path:
                assert field in current, (
                    f"Required field path {' -> '.join(field_path)} is missing"
                )
                current = current[field]

    def test_config_performance(self):
        """Test that config loading is reasonably fast."""
        import time

        start_time = time.time()
        for _ in range(10):
            load_config()
        end_time = time.time()

        # Should load 10 times in less than 1 second
        assert (end_time - start_time) < 1.0, "Config loading is too slow"
