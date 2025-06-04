# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Test environment setup for isolated pytest execution.

This module ensures that:
1. Tests run from the correct working directory
2. Module imports work consistently regardless of invocation location
3. Test artifacts are isolated in the tests directory
4. Coverage data is collected properly
"""

import os
import sys
from pathlib import Path


def setup_test_environment():
    """Set up the test environment for consistent pytest execution."""
    # Determine project root (where this file's parent's parent is)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    tests_dir = current_file.parent

    # Ensure we're running from the project root
    if Path.cwd() != project_root:
        print(f"Changing working directory to: {project_root}")
        os.chdir(project_root)

    # Ensure project root is in Python path for imports
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    # Ensure test directory is accessible
    tests_dir_str = str(tests_dir)
    if tests_dir_str not in sys.path:
        sys.path.append(tests_dir_str)

    # Set environment variables for consistent test behavior
    os.environ["PYTEST_CURRENT_TEST"] = "true"

    # Ensure coverage data directory exists
    coverage_dir = tests_dir / ".coverage_data"
    coverage_dir.mkdir(exist_ok=True)

    print("Test environment setup complete:")
    print(f"  - Working directory: {Path.cwd()}")
    print(f"  - Project root: {project_root}")
    print(f"  - Tests directory: {tests_dir}")
    print(f"  - Python path includes: {project_root_str}")


# Run setup when this module is imported
setup_test_environment()
