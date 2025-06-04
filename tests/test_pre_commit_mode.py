# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for the pre-commit mode functionality.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import get_git_tracked_files, verify


def test_get_git_tracked_files_success():
    """Test successful Git tracked files retrieval."""
    # Mock subprocess.run to simulate git ls-files output
    mock_result = MagicMock()
    mock_result.stdout = "file1.py\nfile2.js\nsubdir/file3.txt\n"
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        tracked_files = get_git_tracked_files(Path("/fake/repo"))

        # Should return set of absolute paths
        assert len(tracked_files) == 3
        # Check that paths are converted to absolute
        assert all(path.is_absolute() for path in tracked_files)


def test_get_git_tracked_files_git_error():
    """Test Git command failure handling."""
    mock_error = subprocess.CalledProcessError(1, ["git", "ls-files"])
    mock_error.stderr = "Not a git repository"

    with patch("subprocess.run", side_effect=mock_error):
        try:
            get_git_tracked_files()
            assert False, "Should have raised CalledProcessError"
        except subprocess.CalledProcessError:
            pass  # Expected


def test_get_git_tracked_files_git_not_found():
    """Test Git not available handling."""
    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        try:
            get_git_tracked_files()
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass  # Expected


def test_verify_with_pre_commit_mode_basic():
    """Test basic pre-commit mode functionality."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        test_file = test_dir / "test.py"
        test_file.write_text(valid_content, encoding="utf-8")

        # Mock Git to return the file as tracked
        mock_result = MagicMock()
        mock_result.stdout = str(test_file.relative_to(test_dir)) + "\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("sys.exit") as mock_exit:
                verify(paths=[str(test_dir)], debug=True, pre_commit_mode=True)
                # Should not exit with error since file is valid
                mock_exit.assert_not_called()

    finally:
        # Clean up
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_verify_without_pre_commit_mode():
    """Test verify function without pre-commit mode."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        test_file = test_dir / "test.py"
        test_file.write_text(valid_content, encoding="utf-8")

        with patch("sys.exit") as mock_exit:
            verify(paths=[str(test_dir)], debug=True, pre_commit_mode=False)
            # Should not exit with error since file is valid
            mock_exit.assert_not_called()

    finally:
        # Clean up
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_verify_single_file_pre_commit_mode_tracked():
    """Test pre-commit mode with a single tracked file."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        test_file = test_dir / "test.py"
        test_file.write_text(valid_content, encoding="utf-8")

        # Mock Git to return the file as tracked
        mock_result = MagicMock()
        mock_result.stdout = str(test_file.relative_to(test_dir.parent)) + "\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("sys.exit") as mock_exit:
                verify(
                    paths=[str(test_file)],  # Single file path
                    debug=True,
                    pre_commit_mode=True,
                )
                # Should not exit with error since file is valid and tracked
                mock_exit.assert_not_called()

    finally:
        # Clean up
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_verify_single_file_pre_commit_mode_untracked():
    """Test pre-commit mode with a single untracked file."""
    test_dir = Path(tempfile.mkdtemp())

    try:
        # Create test file
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        test_file = test_dir / "test.py"
        test_file.write_text(valid_content, encoding="utf-8")

        # Mock Git to return empty (no tracked files)
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("sys.exit") as mock_exit:
                verify(
                    paths=[str(test_file)],  # Single file path
                    debug=True,
                    pre_commit_mode=True,
                )
                # Should not exit with error since no files were processed
                mock_exit.assert_not_called()

    finally:
        # Clean up
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)
