# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Test cases for .gitignore integration functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import SPDXVerifier, load_gitignore_patterns


class TestGitignoreIntegration:
    """Test cases for .gitignore integration functionality."""

    def test_load_gitignore_patterns_existing_file(self):
        """Test loading patterns from an existing .gitignore file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .gitignore file
            gitignore_content = """# Comment line
node_modules/
*.log
dist/

# Another comment
__pycache__/
*.pyc

# Empty lines should be ignored

build/
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            patterns = load_gitignore_patterns(temp_path)

            expected_patterns = [
                "node_modules/",
                "*.log",
                "dist/",
                "__pycache__/",
                "*.pyc",
                "build/",
            ]

            assert len(patterns) == 6
            for pattern in expected_patterns:
                assert pattern in patterns

    def test_load_gitignore_patterns_no_file(self):
        """Test loading patterns when .gitignore doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            patterns = load_gitignore_patterns(temp_path)
            assert patterns == []

    def test_load_gitignore_patterns_empty_file(self):
        """Test loading patterns from empty .gitignore file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text("")

            patterns = load_gitignore_patterns(temp_path)
            assert patterns == []

    def test_load_gitignore_patterns_only_comments(self):
        """Test loading patterns from .gitignore with only comments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gitignore_content = """# This is a comment
# Another comment

# More comments
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            patterns = load_gitignore_patterns(temp_path)
            assert patterns == []

    def test_spdx_verifier_gitignore_integration(self):
        """Test that SPDXVerifier properly integrates .gitignore patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .gitignore file
            gitignore_content = """node_modules/
*.log
build/
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            # Create verifier
            verifier = SPDXVerifier(directory=temp_path, debug=True)

            # Check that gitignore patterns are in skip_patterns
            assert "node_modules/" in verifier.skip_patterns
            assert "*.log" in verifier.skip_patterns
            assert "build/" in verifier.skip_patterns

    def test_spdx_verifier_gitignore_file_skipping(self):
        """Test that files matching .gitignore patterns are actually skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .gitignore file
            gitignore_content = """node_modules/
*.log
build/
*.min.js
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            # Create verifier
            verifier = SPDXVerifier(directory=temp_path, debug=True)

            # Test files that should be skipped
            test_cases = [
                ("node_modules/package.json", True),
                ("app.log", True),
                ("build/output.txt", True),
                ("script.min.js", True),
                ("src/main.py", False),
                ("script.js", False),
                ("README.md", False),
            ]

            for file_path, should_skip in test_cases:
                path_obj = Path(file_path)
                actually_skipped = verifier.should_skip_file(path_obj)
                assert actually_skipped == should_skip, (
                    f"File {file_path}: expected skip={should_skip}, got {actually_skipped}"
                )

    def test_spdx_verifier_combines_all_patterns(self):
        """Test that SPDXVerifier combines default, gitignore, and user patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .gitignore file
            gitignore_content = """custom_ignore/
*.temp
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)

            # Create verifier with user patterns
            user_patterns = ["user_pattern.txt", "*.user"]
            verifier = SPDXVerifier(
                directory=temp_path, skip_patterns=user_patterns, debug=True
            )

            # Check that all pattern types are included
            # Default patterns (from config)
            assert any("__pycache__" in pattern for pattern in verifier.skip_patterns)

            # Gitignore patterns
            assert "custom_ignore/" in verifier.skip_patterns
            assert "*.temp" in verifier.skip_patterns

            # User patterns
            assert "user_pattern.txt" in verifier.skip_patterns
            assert "*.user" in verifier.skip_patterns

    def test_gitignore_patterns_unicode_handling(self):
        """Test that .gitignore files with unicode characters are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .gitignore with unicode content
            gitignore_content = """# Unicode comment: ñáéíóú
normal_pattern/
café_files/
файлы/
"""
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text(gitignore_content, encoding="utf-8")

            patterns = load_gitignore_patterns(temp_path)

            assert "normal_pattern/" in patterns
            assert "café_files/" in patterns
            assert "файлы/" in patterns

    def test_gitignore_patterns_io_error_handling(self):
        """Test graceful handling of IO errors when reading .gitignore."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gitignore_path = temp_path / ".gitignore"
            gitignore_path.write_text("test_pattern/")

            # Mock an IO error
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                patterns = load_gitignore_patterns(temp_path)
                assert patterns == []  # Should return empty list on error

    def test_spdx_verifier_no_gitignore_file(self):
        """Test SPDXVerifier when no .gitignore file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create verifier without .gitignore file
            verifier = SPDXVerifier(directory=temp_path, debug=True)

            # Should still have default patterns
            assert len(verifier.skip_patterns) > 0
            # Should contain default patterns
            assert any("__pycache__" in pattern for pattern in verifier.skip_patterns)
