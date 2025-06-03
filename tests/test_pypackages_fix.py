# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Test the specific fix for __pypackages__ cache directory exclusion.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import SPDXVerifier, load_config


class TestPypackagesFix:
    """Test the specific fix for __pypackages__ cache directory exclusion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_pypackages_structure(self):
        """Create a realistic __pypackages__ directory structure."""
        pypackages_dir = self.test_dir / "__pypackages__"

        # Create typical PDM cache structure
        structure = {
            "3.9": {
                "bin": {
                    "black": "#!/usr/bin/env python\n# black executable",
                    "pytest": "#!/usr/bin/env python\n# pytest executable",
                    "spdx-verify": "#!/usr/bin/env python\n# spdx-verify executable",
                },
                "lib": {
                    "black": {
                        "__init__.py": "# black package",
                        "main.py": "# black main module",
                    },
                    "pytest": {
                        "__init__.py": "# pytest package",
                        "main.py": "# pytest main module",
                    },
                    "_pytest": {
                        "__init__.py": "# _pytest package",
                        "fixtures.py": "# pytest fixtures",
                    },
                    "click": {
                        "__init__.py": "# click package",
                        "core.py": "# click core module",
                    },
                    "__pycache__": {
                        "module.cpython-39.pyc": b"\x00\x01\x02\x03"  # binary cache file
                    },
                },
                "include": {},  # Usually empty
            },
            "3.10": {
                "lib": {
                    "different_package": {
                        "__init__.py": "# different package for py3.10"
                    }
                }
            },
        }

        self._create_structure(pypackages_dir, structure)
        return pypackages_dir

    def _create_structure(self, base_path: Path, structure: dict):
        """Recursively create directory structure."""
        for name, content in structure.items():
            path = base_path / name

            if isinstance(content, dict):
                path.mkdir(parents=True, exist_ok=True)
                self._create_structure(path, content)
            elif isinstance(content, str):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            elif isinstance(content, bytes):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

    def test_pypackages_in_default_skip_patterns(self):
        """Test that __pypackages__ is in default skip patterns."""
        config = load_config()
        skip_patterns = config.get("default_skip_patterns", [])

        # Should have a pattern that matches __pypackages__
        pypackages_patterns = [p for p in skip_patterns if "__pypackages__" in p]
        assert len(pypackages_patterns) > 0, "Should have __pypackages__ skip pattern"

        # Should be a glob pattern that covers subdirectories
        has_recursive_pattern = any("**" in p for p in pypackages_patterns)
        assert has_recursive_pattern, "Should have recursive pattern for __pypackages__"

    def test_verifier_includes_default_skip_patterns(self):
        """Test that SPDXVerifier includes default skip patterns."""
        verifier = SPDXVerifier()

        # Should have default skip patterns loaded
        assert len(verifier.skip_patterns) > 0

        # Should include __pypackages__ pattern
        pypackages_patterns = [
            p for p in verifier.skip_patterns if "__pypackages__" in p
        ]
        assert len(pypackages_patterns) > 0, (
            "Verifier should have __pypackages__ skip pattern"
        )

    def test_verifier_merges_user_and_default_patterns(self):
        """Test that user patterns are merged with default patterns."""
        user_patterns = ["custom_pattern.txt", "temp_*.log"]
        verifier = SPDXVerifier(skip_patterns=user_patterns)

        # Should have both user and default patterns
        for pattern in user_patterns:
            assert pattern in verifier.skip_patterns, (
                f"Should have user pattern: {pattern}"
            )

        # Should still have default patterns
        pypackages_patterns = [
            p for p in verifier.skip_patterns if "__pypackages__" in p
        ]
        assert len(pypackages_patterns) > 0, (
            "Should still have __pypackages__ default pattern"
        )

    def test_pypackages_files_are_skipped(self):
        """Test that files in __pypackages__ are actually skipped."""
        # Create __pypackages__ structure
        self.create_pypackages_structure()

        # Create a regular source file that should NOT be skipped
        source_file = self.test_dir / "main.py"
        source_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def main():
    pass
"""
        source_file.write_text(source_content, encoding="utf-8")

        # Run verification
        verifier = SPDXVerifier(debug=True)
        result = verifier.verify_directory(self.test_dir)

        # The source file should be checked
        assert verifier.stats["checked"] > 0, "Should check at least the source file"

        # __pypackages__ files should be skipped
        assert verifier.stats["skipped"] > 10, "Should skip many __pypackages__ files"

        # Should have passed (only checking the valid source file)
        assert result is True, "Should pass when only valid files are checked"

    def test_pypackages_individual_file_skip_check(self):
        """Test individual file skip checking for __pypackages__ files."""
        verifier = SPDXVerifier()

        test_cases = [
            "__pypackages__/3.9/lib/black/__init__.py",
            "__pypackages__/3.9/bin/black",
            "__pypackages__/3.10/lib/pytest/main.py",
            "__pypackages__/3.9/lib/__pycache__/module.pyc",
        ]

        for file_path in test_cases:
            path = Path(file_path)
            should_skip = verifier.should_skip_file(path)
            assert should_skip, f"File {file_path} should be skipped"

    def test_pypackages_vs_regular_packages(self):
        """Test that __pypackages__ is skipped but regular packages are not."""
        verifier = SPDXVerifier()

        # __pypackages__ files should be skipped
        pypackages_files = [
            "__pypackages__/3.9/lib/package/__init__.py",
            "__pypackages__/3.9/bin/script",
        ]

        for file_path in pypackages_files:
            should_skip = verifier.should_skip_file(Path(file_path))
            assert should_skip, f"__pypackages__ file {file_path} should be skipped"

        # Regular package files should NOT be skipped
        regular_files = [
            "packages/mypackage/__init__.py",
            "src/packages/utils.py",
            "my_pypackages/file.py",  # Different name
        ]

        for file_path in regular_files:
            should_skip = verifier.should_skip_file(Path(file_path))
            assert not should_skip, f"Regular file {file_path} should NOT be skipped"

    def test_pypackages_pattern_specificity(self):
        """Test that __pypackages__ pattern is specific enough."""

        verifier = SPDXVerifier()

        # Should skip __pypackages__ but not similar names
        test_cases = [
            ("__pypackages__/file.py", True),  # Should skip
            ("__pypackages__/3.9/lib/pkg/file.py", True),  # Should skip
            ("pypackages/file.py", False),  # Should NOT skip (no underscores)
            (
                "src/__pypackages__/file.py",
                False,
            ),  # Currently does NOT skip (pattern is root-level)
            ("my_pypackages/file.py", False),  # Should NOT skip (different prefix)
            (
                "__pypackages_backup__/file.py",
                False,
            ),  # Should NOT skip (different suffix)
        ]

        for file_path, should_be_skipped in test_cases:
            is_skipped = verifier.should_skip_file(Path(file_path))
            if should_be_skipped:
                assert is_skipped, f"File {file_path} should be skipped"
            else:
                assert not is_skipped, f"File {file_path} should NOT be skipped"

    def test_original_issue_scenario(self):
        """Test the exact scenario from the original issue."""
        # Create the scenario: __pypackages__ with many files, plus a few real source files
        self.create_pypackages_structure()

        # Create some real source files
        source_files = [
            (
                "src/main.py",
                """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def main():
    pass
""",
            ),
            (
                "tests/test_main.py",
                """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def test_main():
    pass
""",
            ),
            (
                "README.md",
                """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Project README
""",
            ),
        ]

        for file_path, content in source_files:
            full_path = self.test_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Run verification (this was the original problem scenario)
        verifier = SPDXVerifier(debug=True)
        result = verifier.verify_directory(self.test_dir)

        # Should check only the real source files, not cache files
        assert verifier.stats["checked"] == len(source_files), (
            f"Should check {len(source_files)} source files"
        )

        # Should skip many cache files
        assert verifier.stats["skipped"] > 10, "Should skip many __pypackages__ files"

        # Should pass (all source files have valid headers)
        assert result is True, "Should pass verification"

    def test_e2e_verification_with_pypackages(self):
        """End-to-end test of the verification with __pypackages__ present."""
        import subprocess
        import sys

        # Create test structure
        self.create_pypackages_structure()

        # Create a valid Python file
        source_file = self.test_dir / "test.py"
        source_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        source_file.write_text(source_content, encoding="utf-8")

        # Run the actual spdx_verify.py script
        script_path = Path(__file__).parent.parent / "spdx_verify.py"
        cmd = [sys.executable, str(script_path), str(self.test_dir), "--debug"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Should succeed
        assert result.returncode == 0, (
            f"Verification failed: {result.stdout}\n{result.stderr}"
        )

        # Should show skipped files
        assert (
            "Skipped:" in result.stdout
            and "2845" not in result.stdout
            or "⏩ SKIP" in result.stdout
        )

        # Should check only a few files (not thousands)
        assert "Files checked:" in result.stdout

        # Extract the number of files checked (should be small, not 2845+)
        import re

        checked_match = re.search(r"Files checked: (\d+)", result.stdout)
        if checked_match:
            files_checked = int(checked_match.group(1))
            assert files_checked < 10, (
                f"Should check only a few files, not {files_checked}"
            )

    def test_pattern_matching_performance(self):
        """Test that pattern matching doesn't significantly slow down verification."""
        import time

        # Create many files in __pypackages__
        pypackages_dir = self.test_dir / "__pypackages__"
        for i in range(100):
            file_path = pypackages_dir / "3.9" / "lib" / f"package_{i}" / "__init__.py"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("# package content", encoding="utf-8")

        # Create one source file
        source_file = self.test_dir / "main.py"
        source_file.write_text(
            """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def main(): pass
""",
            encoding="utf-8",
        )

        # Time the verification
        start_time = time.time()

        verifier = SPDXVerifier()
        verifier.verify_directory(self.test_dir)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete quickly (less than 5 seconds even with 100 files)
        assert duration < 5.0, f"Verification took too long: {duration} seconds"

        # Should have skipped the cache files efficiently
        assert verifier.stats["skipped"] >= 100
        assert verifier.stats["checked"] == 1  # Only the source file

    def test_config_modification_doesnt_break_fix(self):
        """Test that the fix works even if config is modified."""
        # Test with custom config that might not have __pypackages__ pattern
        custom_config = {
            "languages": {"python": {"comment_prefix": "#", "extensions": [".py"]}},
            "default_skip_patterns": [
                "*.pyc",
                ".git/**",
                # Intentionally missing __pypackages__
            ],
        }

        with patch("spdx_verify.load_config", return_value=custom_config):
            # Even with custom config, user can still provide __pypackages__ skip pattern
            verifier = SPDXVerifier(skip_patterns=["__pypackages__/**"])

            should_skip = verifier.should_skip_file(
                Path("__pypackages__/3.9/lib/pkg/file.py")
            )
            assert should_skip, (
                "Should still skip __pypackages__ with user-provided pattern"
            )
