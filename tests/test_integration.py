# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Integration tests for the verify() function and CLI interface.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import verify, main


class TestVerifyFunction:
    """Test the main verify() function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

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

    def test_verify_single_file_success(self):
        """Test verifying a single valid file."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")

        # Should not raise SystemExit for successful verification
        verify(paths=[str(file_path)], debug=True)

    def test_verify_single_file_failure(self):
        """Test verifying a single invalid file."""
        content = """def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")

        # Should raise SystemExit(1) for failed verification
        with pytest.raises(SystemExit) as exc_info:
            verify(paths=[str(file_path)], debug=True)
        assert exc_info.value.code == 1

    def test_verify_directory_success(self):
        """Test verifying a directory with all valid files."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(content, "file1.py")
        self.create_test_file(content, "file2.py")

        # Should not raise SystemExit for successful verification
        verify(paths=[str(self.test_dir)], debug=True)

    def test_verify_directory_failure(self):
        """Test verifying a directory with some invalid files."""
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

        # Should raise SystemExit(1) for failed verification
        with pytest.raises(SystemExit) as exc_info:
            verify(paths=[str(self.test_dir)], debug=True)
        assert exc_info.value.code == 1

    def test_verify_multiple_paths(self):
        """Test verifying multiple paths."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file1 = self.create_test_file(content, "file1.py")
        file2 = self.create_test_file(content, "file2.py")

        # Should not raise SystemExit for successful verification
        verify(paths=[str(file1), str(file2)], debug=True)

    def test_verify_nonexistent_path(self, capsys):
        """Test verifying non-existent path."""
        nonexistent = "/path/that/does/not/exist"

        # Should raise SystemExit(1) for non-existent path
        with pytest.raises(SystemExit) as exc_info:
            verify(paths=[nonexistent], debug=True)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_verify_custom_license(self):
        """Test verifying with custom license."""
        content = """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Custom Corp

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")

        # Should pass with correct license
        verify(
            paths=[str(file_path)],
            license="MIT",
            copyright_holder="Custom Corp",
            debug=True,
        )

    def test_verify_with_skip_patterns(self):
        """Test verifying with skip patterns."""
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

        # Should pass when invalid file is skipped
        verify(paths=[str(self.test_dir)], skip="skip_*.py", debug=True)

    def test_verify_default_path(self):
        """Test verify with default path (current directory)."""
        # Test with empty paths list
        with patch("spdx_verify.SPDXVerifier") as mock_verifier_class:
            mock_verifier = Mock()
            mock_verifier.stats = {"checked": 0, "passed": 0}
            mock_verifier_class.return_value = mock_verifier

            verify(paths=[])

            # Should use current directory "."
            mock_verifier_class.assert_called_once()

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch("spdx_verify.set_github_output")
    def test_verify_github_actions_outputs(self, mock_set_output, mock_is_gha):
        """Test that GitHub Actions outputs are set."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")

        verify(paths=[str(file_path)], debug=True)

        # Should set GitHub Actions outputs
        assert mock_set_output.call_count >= 2  # At least passed and files_checked

        # Check specific outputs
        output_calls = {
            call[0][0]: call[0][1] for call in mock_set_output.call_args_list
        }
        assert "passed" in output_calls
        assert "files_checked" in output_calls


class TestMainFunction:
    """Test the main() function and CLI interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch.dict(
        os.environ,
        {
            "INPUT_LICENSE": "MIT",
            "INPUT_COPYRIGHT": "Test Corp",
            "INPUT_PATHS": "src,tests",
            "INPUT_SKIP": "*.min.js",
            "INPUT_DEBUG": "true",
        },
    )
    @patch("spdx_verify.verify")
    def test_main_github_actions_mode(self, mock_verify, mock_is_gha):
        """Test main function in GitHub Actions mode."""
        main()

        mock_verify.assert_called_once_with(
            paths=["src", "tests"],
            license="MIT",
            copyright_holder="Test Corp",
            skip="*.min.js",
            debug=True,
            pre_commit_mode=False,
            reuse_compliance=False,
        )

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch.dict(os.environ, {}, clear=True)
    @patch("spdx_verify.verify")
    def test_main_github_actions_mode_defaults(self, mock_verify, mock_is_gha):
        """Test main function in GitHub Actions mode with defaults."""
        main()

        mock_verify.assert_called_once_with(
            paths=["."],
            license="Apache-2.0",
            copyright_holder="The Linux Foundation",
            skip=None,
            debug=False,
            pre_commit_mode=False,
            reuse_compliance=False,
        )

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer")
    def test_main_cli_mode_with_typer(self, mock_typer, mock_is_gha):
        """Test main function in CLI mode with typer available."""
        mock_app = Mock()
        mock_typer.Typer.return_value = mock_app

        main()

        mock_typer.Typer.assert_called_once()
        mock_app.assert_called_once()

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("sys.argv", ["spdx_verify.py", "test_dir", "--license", "MIT"])
    @patch("spdx_verify.verify")
    def test_main_cli_mode_without_typer(self, mock_verify, mock_is_gha):
        """Test main function in CLI mode without typer (argparse fallback)."""
        main()

        # Should use argparse and call verify
        mock_verify.assert_called_once()
        call_args = mock_verify.call_args
        # Verify the paths argument contains 'test_dir'
        assert "test_dir" in call_args[1]["paths"]
        assert call_args[1]["license"] == "MIT"

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("sys.argv", ["spdx_verify.py", "--help"])
    def test_main_cli_help(self, mock_is_gha):
        """Test main function with help argument."""
        # Should raise SystemExit for help
        with pytest.raises(SystemExit):
            main()

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("sys.argv", ["spdx_verify.py"])
    @patch("spdx_verify.verify")
    def test_main_cli_no_args(self, mock_verify, mock_is_gha):
        """Test main function with no arguments (should use current directory)."""
        main()

        # Should use default path "."
        call_args = mock_verify.call_args
        assert "." in call_args[1]["paths"]


class TestCLIArguments:
    """Test CLI argument parsing."""

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("spdx_verify.verify")
    def test_cli_debug_flag(self, mock_verify, mock_is_gha):
        """Test CLI debug flag."""
        with patch("sys.argv", ["spdx_verify.py", "--debug"]):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["debug"] is True

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("spdx_verify.verify")
    def test_cli_license_option(self, mock_verify, mock_is_gha):
        """Test CLI license option."""
        with patch("sys.argv", ["spdx_verify.py", "--license", "MIT"]):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["license"] == "MIT"

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("spdx_verify.verify")
    def test_cli_copyright_option(self, mock_verify, mock_is_gha):
        """Test CLI copyright option."""
        with patch("sys.argv", ["spdx_verify.py", "--copyright", "Custom Corp"]):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["copyright_holder"] == "Custom Corp"

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("spdx_verify.verify")
    def test_cli_skip_option(self, mock_verify, mock_is_gha):
        """Test CLI skip option."""
        with patch("sys.argv", ["spdx_verify.py", "--skip", "*.min.js"]):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["skip"] == "*.min.js"

    @patch("spdx_verify.is_github_actions", return_value=False)
    @patch("spdx_verify.typer", None)
    @patch("spdx_verify.verify")
    def test_cli_multiple_paths(self, mock_verify, mock_is_gha):
        """Test CLI with multiple paths."""
        with patch("sys.argv", ["spdx_verify.py", "src", "tests", "docs"]):
            main()

            call_args = mock_verify.call_args
            assert "src" in call_args[1]["paths"]
            assert "tests" in call_args[1]["paths"]
            assert "docs" in call_args[1]["paths"]


class TestEnvironmentVariables:
    """Test environment variable handling in GitHub Actions mode."""

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch("spdx_verify.verify")
    def test_github_actions_env_boolean_true(self, mock_verify, mock_is_gha):
        """Test GitHub Actions boolean environment variable parsing."""
        with patch.dict(os.environ, {"INPUT_DEBUG": "true"}):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["debug"] is True

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch("spdx_verify.verify")
    def test_github_actions_env_boolean_false(self, mock_verify, mock_is_gha):
        """Test GitHub Actions boolean environment variable parsing."""
        with patch.dict(os.environ, {"INPUT_DEBUG": "false"}):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["debug"] is False

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch("spdx_verify.verify")
    def test_github_actions_env_paths_parsing(self, mock_verify, mock_is_gha):
        """Test GitHub Actions paths environment variable parsing."""
        with patch.dict(os.environ, {"INPUT_PATHS": "src, tests , docs"}):
            main()

            call_args = mock_verify.call_args
            # Should split and strip whitespace
            assert call_args[1]["paths"] == ["src", "tests", "docs"]

    @patch("spdx_verify.is_github_actions", return_value=True)
    @patch("spdx_verify.verify")
    def test_github_actions_env_empty_skip(self, mock_verify, mock_is_gha):
        """Test GitHub Actions empty skip environment variable."""
        with patch.dict(os.environ, {"INPUT_SKIP": ""}):
            main()

            call_args = mock_verify.call_args
            assert call_args[1]["skip"] is None
