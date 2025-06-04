# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
End-to-end tests for SPDX verification tool.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest


class TestEndToEnd:
    """End-to-end tests using subprocess to test the actual CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Use absolute path from project root to ensure consistency
        self.script_path = Path(__file__).parent.parent / "spdx_verify.py"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_file(self, content: str, filename: str) -> Path:
        """Create a test file with given content."""
        file_path = self.test_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def run_spdx_verify(
        self, args: list, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        """Run spdx_verify.py with given arguments."""
        cmd = [sys.executable, str(self.script_path)] + args
        return subprocess.run(
            cmd, cwd=cwd or self.test_dir, capture_output=True, text=True
        )

    def test_valid_file_success(self):
        """Test successful verification of valid file."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "valid.py")

        result = self.run_spdx_verify([str(file_path), "--debug"])
        assert result.returncode == 0
        assert "✅ PASS" in result.stdout or "VERIFICATION SUMMARY" in result.stdout

    def test_invalid_file_failure(self):
        """Test failure on invalid file."""
        content = """def hello():
    pass
"""
        file_path = self.create_test_file(content, "invalid.py")

        result = self.run_spdx_verify([str(file_path), "--debug"])
        assert result.returncode == 1
        assert "❌ FAIL" in result.stdout

    def test_directory_verification(self):
        """Test directory verification."""
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(valid_content, "valid1.py")
        self.create_test_file(valid_content, "valid2.py")

        result = self.run_spdx_verify([str(self.test_dir), "--debug"])
        assert result.returncode == 0
        assert "Files checked: 2" in result.stdout

    def test_mixed_directory_verification(self):
        """Test directory with both valid and invalid files."""
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        invalid_content = """def hello():
    pass
"""
        self.create_test_file(valid_content, "valid.py")
        self.create_test_file(invalid_content, "invalid.py")

        result = self.run_spdx_verify([str(self.test_dir), "--debug"])
        assert result.returncode == 1
        assert "Files checked: 2" in result.stdout
        assert "Passed: 1" in result.stdout
        assert "Failed: 1" in result.stdout

    def test_custom_license(self):
        """Test verification with custom license."""
        content = """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Custom Corp

def hello():
    pass
"""
        file_path = self.create_test_file(content, "mit.py")

        result = self.run_spdx_verify(
            [
                str(file_path),
                "--license",
                "MIT",
                "--copyright",
                "Custom Corp",
                "--debug",
            ]
        )
        assert result.returncode == 0

    def test_skip_patterns(self):
        """Test skip patterns functionality."""
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        invalid_content = """def hello():
    pass
"""
        self.create_test_file(valid_content, "valid.py")
        self.create_test_file(invalid_content, "skip_me.py")

        result = self.run_spdx_verify(
            [str(self.test_dir), "--skip", "skip_*.py", "--debug"]
        )
        assert result.returncode == 0
        assert "⏩ SKIP" in result.stdout or "Skipped:" in result.stdout

    def test_help_option(self):
        """Test help option."""
        result = self.run_spdx_verify(["--help"])
        # Help should exit with 0 in most CLI tools
        assert result.returncode in [0, 2]  # argparse sometimes uses 2 for help
        assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout

    def test_nonexistent_path(self):
        """Test handling of non-existent paths."""
        result = self.run_spdx_verify(["/path/that/does/not/exist", "--debug"])
        assert result.returncode == 1
        assert "does not exist" in result.stdout

    def test_javascript_file(self):
        """Test JavaScript file verification."""
        content = """// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 The Linux Foundation

function hello() {
    console.log("Hello");
}
"""
        file_path = self.create_test_file(content, "test.js")

        result = self.run_spdx_verify([str(file_path), "--debug"])
        assert result.returncode == 0

    def test_css_file(self):
        """Test CSS file verification."""
        content = """/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: 2025 The Linux Foundation */

body {
    margin: 0;
}
"""
        file_path = self.create_test_file(content, "test.css")

        result = self.run_spdx_verify([str(file_path), "--debug"])
        assert result.returncode == 0

    def test_unknown_file_type_skipped(self):
        """Test that unknown file types are handled with default file type disabled."""
        content = """This is an unknown file type
without any headers
"""
        file_path = self.create_test_file(content, "unknown.xyz")

        result = self.run_spdx_verify(
            [str(file_path), "--debug", "--disable-default-file-type"]
        )
        assert result.returncode == 0  # Should be skipped, not failed
        assert "unknown.xyz" in result.stdout
        assert "SKIP" in result.stdout or "unknown file type" in result.stdout

    def test_summary_output(self):
        """Test that summary is properly displayed."""
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(valid_content, "test.py")

        result = self.run_spdx_verify([str(self.test_dir), "--debug"])
        assert result.returncode == 0
        assert "📊 VERIFICATION SUMMARY" in result.stdout
        assert "Files checked:" in result.stdout
        assert "Passed:" in result.stdout
        assert "Skipped:" in result.stdout

    def test_with_real_test_files(self):
        """Test with the actual test_files directory if it exists."""
        test_files_dir = Path(__file__).parent / "test_files"

        if test_files_dir.exists():
            result = self.run_spdx_verify([str(test_files_dir), "--debug"])

            # Should complete (pass or fail based on test files content)
            assert result.returncode in [0, 1]
            assert "📊 VERIFICATION SUMMARY" in result.stdout
            assert "Files checked:" in result.stdout


@pytest.mark.skipif(not os.getenv("GITHUB_ACTIONS"), reason="GitHub Actions tests")
class TestGitHubActionsMode:
    """Test GitHub Actions mode using environment variables."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Use absolute path from project root to ensure consistency
        self.script_path = Path(__file__).parent.parent / "spdx_verify.py"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_file(self, content: str, filename: str) -> Path:
        """Create a test file with given content."""
        file_path = self.test_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def run_spdx_verify_gha(self, env_vars: dict) -> subprocess.CompletedProcess:
        """Run spdx_verify.py in GitHub Actions mode."""
        env = os.environ.copy()
        env.update(env_vars)
        env["GITHUB_ACTIONS"] = "true"

        cmd = [sys.executable, str(self.script_path)]
        return subprocess.run(
            cmd, cwd=self.test_dir, env=env, capture_output=True, text=True
        )

    def test_github_actions_success(self):
        """Test GitHub Actions mode with successful verification."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(content, "test.py")

        result = self.run_spdx_verify_gha(
            {"INPUT_PATHS": str(self.test_dir), "INPUT_DEBUG": "true"}
        )

        assert result.returncode == 0
        assert "📊 VERIFICATION SUMMARY" in result.stdout

    def test_github_actions_failure(self):
        """Test GitHub Actions mode with failed verification."""
        content = """def hello():
    pass
"""
        self.create_test_file(content, "test.py")

        result = self.run_spdx_verify_gha(
            {"INPUT_PATHS": str(self.test_dir), "INPUT_DEBUG": "true"}
        )

        assert result.returncode == 1
        assert "❌ FAIL" in result.stdout

    def test_github_actions_custom_settings(self):
        """Test GitHub Actions mode with custom license and copyright."""
        content = """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Custom Corp

def hello():
    pass
"""
        self.create_test_file(content, "test.py")

        result = self.run_spdx_verify_gha(
            {
                "INPUT_PATHS": str(self.test_dir),
                "INPUT_LICENSE": "MIT",
                "INPUT_COPYRIGHT": "Custom Corp",
                "INPUT_DEBUG": "true",
            }
        )

        assert result.returncode == 0


class TestPerformance:
    """Test performance with larger file sets."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Use absolute path from project root to ensure consistency
        self.script_path = Path(__file__).parent.parent / "spdx_verify.py"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_file(self, content: str, filename: str) -> Path:
        """Create a test file with given content."""
        file_path = self.test_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_many_files_performance(self):
        """Test performance with many files."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""

        # Create 50 test files
        for i in range(50):
            self.create_test_file(content, f"test_{i:03d}.py")

        cmd = [sys.executable, str(self.script_path), str(self.test_dir), "--debug"]
        start_time = __import__("time").time()

        result = subprocess.run(cmd, capture_output=True, text=True)

        end_time = __import__("time").time()
        duration = end_time - start_time

        assert result.returncode == 0
        assert "Files checked: 50" in result.stdout
        # Should complete in reasonable time (less than 30 seconds)
        assert duration < 30

    def test_deep_directory_structure(self):
        """Test with deep directory structure."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""

        # Create nested directories
        for i in range(5):
            for j in range(3):
                dir_path = self.test_dir / f"level{i}" / f"sublevel{j}"
                dir_path.mkdir(parents=True, exist_ok=True)
                file_path = dir_path / f"test_{i}_{j}.py"
                file_path.write_text(content, encoding="utf-8")

        cmd = [sys.executable, str(self.script_path), str(self.test_dir), "--debug"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0
        assert "Files checked: 15" in result.stdout
