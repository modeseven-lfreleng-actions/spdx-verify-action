# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Test fixtures and configuration for pytest test suite.

This configuration ensures tests are isolated and don't depend on the current working directory.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

# Ensure the project root is in the Python path for imports
# This is more robust than using sys.path.insert() in individual test files
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Change to project root directory to ensure consistent test behavior
# regardless of where pytest is invoked from
os.chdir(PROJECT_ROOT)


@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """
    Session-scoped fixture to ensure test isolation.
    This ensures consistent behavior regardless of working directory.
    """
    # Store original state
    original_cwd = Path.cwd()
    original_path = sys.path.copy()

    # Ensure we're in the project root
    os.chdir(PROJECT_ROOT)

    # Ensure project root is in path
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    yield PROJECT_ROOT

    # Cleanup: restore original state if needed
    # Note: In most cases we want to keep the working directory as project root
    # but restore path for safety - only if we're not in a test environment
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        os.chdir(original_cwd)
        sys.path[:] = original_path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path

    # Cleanup
    import shutil

    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_files():
    """Sample file contents for testing."""
    return {
        "valid_python": """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
""",
        "invalid_python": """def hello():
    pass
""",
        "missing_license_python": """# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
""",
        "missing_copyright_python": """# SPDX-License-Identifier: Apache-2.0

def hello():
    pass
""",
        "wrong_license_python": """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
""",
        "wrong_copyright_python": """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Wrong Corp

def hello():
    pass
""",
        "valid_javascript": """// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 The Linux Foundation

function hello() {
    console.log("Hello");
}
""",
        "valid_css": """/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: 2025 The Linux Foundation */

body {
    margin: 0;
}
""",
        "valid_html": """<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2025 The Linux Foundation -->

<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>
""",
        "mit_license_python": """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 Custom Corp

def hello():
    pass
""",
        "unknown_file_type": """This is content for an unknown file type.
It doesn't have any headers and should be skipped.
""",
        "binary_like_content": "\x00\x01\x02\x03This looks like binary content\x04\x05",
        "unicode_content": """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
# Unicode test: ñáéíóú 中文 🎉

def hello():
    print("Hola mundo! 🌍")
""",
        "long_lines": """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
# """
        + "x" * 1000
        + """

def hello():
    pass
""",
        "empty_file": "",
        "only_whitespace": """




""",
        "multiline_comment_css": """/*
 * SPDX-License-Identifier: Apache-2.0
 * SPDX-FileCopyrightText: 2025 The Linux Foundation
 */

.class {
    color: red;
}
""",
    }


@pytest.fixture
def file_creator(temp_dir, sample_files):
    """Factory function to create test files."""

    def create_files(file_specs: List[Dict[str, str]]) -> Dict[str, Path]:
        """
        Create test files from specifications.

        Args:
            file_specs: List of dicts with 'name', 'content_key', and optional 'path'
                       Example: [{'name': 'test.py', 'content_key': 'valid_python'}]

        Returns:
            Dict mapping file names to their paths
        """
        created_files = {}

        for spec in file_specs:
            name = spec["name"]
            content_key = spec["content_key"]
            relative_path = spec.get("path", "")

            # Create directory structure if needed
            if relative_path:
                full_dir = temp_dir / relative_path
                full_dir.mkdir(parents=True, exist_ok=True)
                file_path = full_dir / name
            else:
                file_path = temp_dir / name

            # Get content
            if content_key == "custom":
                content = spec["content"]
            else:
                content = sample_files[content_key]

            # Write file
            if isinstance(content, str):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_bytes(content)

            created_files[name] = file_path

        return created_files

    return create_files


@pytest.fixture
def spdx_verifier():
    """Create a basic SPDXVerifier instance for testing."""
    # Import is available due to setup_test_environment fixture
    from spdx_verify import SPDXVerifier

    return SPDXVerifier(debug=True)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "languages": {
            "python": {"comment_prefix": "#", "extensions": [".py", ".pyx", ".pyi"]},
            "javascript": {
                "comment_prefix": "//",
                "extensions": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
            },
            "css": {
                "comment_prefix": "/*",
                "comment_suffix": "*/",
                "extensions": [".css", ".scss", ".sass", ".less"],
            },
            "html": {
                "comment_prefix": "<!--",
                "comment_suffix": "-->",
                "extensions": [".html", ".htm", ".xml"],
            },
            "dockerfile": {
                "comment_prefix": "#",
                "filenames": ["Dockerfile", "dockerfile"],
            },
            "makefile": {
                "comment_prefix": "#",
                "filenames": ["Makefile", "makefile", "GNUmakefile"],
            },
        },
        "default_skip_patterns": [
            "__pycache__/**",
            "*.pyc",
            ".git/**",
            ".svn/**",
            "node_modules/**",
            "*.min.js",
            "*.min.css",
            ".DS_Store",
            "*.egg-info/**",
            "dist/**",
            "build/**",
            ".pytest_cache/**",
            ".mypy_cache/**",
            ".coverage",
            "coverage.xml",
            "*.log",
            "__pypackages__/**",
        ],
        "default_file_type": {"enabled": False, "language": "python"},
    }


class TestDataGenerator:
    """Helper class to generate test data."""

    @staticmethod
    def create_directory_structure(base_dir: Path, structure: dict):
        """
        Create a directory structure from a nested dict.

        Args:
            base_dir: Base directory to create structure in
            structure: Dict where keys are dir/file names and values are:
                      - dict: subdirectory (recursive)
                      - str: file content
                      - None: empty directory
        """
        for name, content in structure.items():
            path = base_dir / name

            if isinstance(content, dict):
                # It's a directory
                path.mkdir(exist_ok=True)
                TestDataGenerator.create_directory_structure(path, content)
            elif isinstance(content, str):
                # It's a file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            elif content is None:
                # Empty directory
                path.mkdir(exist_ok=True)

    @staticmethod
    def create_project_structure(
        base_dir: Path, valid_content: str, invalid_content: str
    ):
        """Create a realistic project structure for testing."""
        structure = {
            "src": {
                "__init__.py": valid_content,
                "main.py": valid_content,
                "utils": {
                    "__init__.py": valid_content,
                    "helpers.py": valid_content,
                    "broken.py": invalid_content,  # One invalid file
                },
            },
            "tests": {
                "__init__.py": valid_content,
                "test_main.py": valid_content,
                "test_utils.py": valid_content,
            },
            "docs": {"README.md": valid_content, "setup.py": valid_content},
            "static": {
                "css": {
                    "style.css": valid_content.replace("#", "/*").replace(
                        "\n", " */\n", 1
                    ),
                    "style.min.css": "/* minified css */",  # Should be skipped
                },
                "js": {
                    "app.js": valid_content.replace("#", "//"),
                    "app.min.js": "// minified js",  # Should be skipped
                },
            },
            "node_modules": {  # Should be skipped entirely
                "package": {"index.js": "// no headers here"}
            },
            ".git": {"config": "git config content"},  # Should be skipped entirely
            "__pycache__": {
                "cache.pyc": "binary cache content"
            },  # Should be skipped entirely
            "build": None,  # Empty directory that should be skipped
            "dist": None,  # Empty directory that should be skipped
        }

        TestDataGenerator.create_directory_structure(base_dir, structure)
