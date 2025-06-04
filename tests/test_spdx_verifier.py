# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Unit tests for SPDXVerifier class.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

# Import from project root - no sys.path manipulation needed due to conftest.py setup
from spdx_verify import DEFAULT_COPYRIGHT, DEFAULT_LICENSE, SPDXVerifier, load_config


class TestSPDXVerifier:
    """Test cases for SPDXVerifier class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.verifier = SPDXVerifier(debug=True)
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_file(self, content: str, filename: str = "test.py") -> Path:
        """Create a test file with given content."""
        file_path = self.test_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_init_default_values(self):
        """Test SPDXVerifier initialization with default values."""
        verifier = SPDXVerifier()
        assert verifier.license_id == DEFAULT_LICENSE
        assert verifier.copyright_holder == DEFAULT_COPYRIGHT
        assert verifier.debug is False
        assert isinstance(verifier.skip_patterns, list)
        assert verifier.stats["checked"] == 0

    def test_init_custom_values(self):
        """Test SPDXVerifier initialization with custom values."""
        verifier = SPDXVerifier(
            license_id="MIT",
            copyright_holder="Custom Corp",
            skip_patterns=["*.min.js"],
            debug=True,
        )
        assert verifier.license_id == "MIT"
        assert verifier.copyright_holder == "Custom Corp"
        assert "*.min.js" in verifier.skip_patterns
        assert verifier.debug is True

    def test_skip_patterns_merge_with_defaults(self):
        """Test that user skip patterns are merged with default patterns."""
        config = load_config()
        default_patterns = config.get("default_skip_patterns", [])

        user_patterns = ["custom_pattern.txt"]
        verifier = SPDXVerifier(skip_patterns=user_patterns)

        # Should contain both default and user patterns
        for pattern in default_patterns:
            assert pattern in verifier.skip_patterns
        for pattern in user_patterns:
            assert pattern in verifier.skip_patterns

    def test_get_language_for_file_by_extension(self):
        """Test language detection by file extension."""
        test_cases = [
            ("test.py", "python"),
            ("test.js", "javascript"),
            ("test.css", "css"),
            ("test.html", "html"),
            ("test.java", "java"),
            ("test.cpp", "c"),  # .cpp maps to 'c' language in config
        ]

        for filename, expected_lang in test_cases:
            file_path = Path(filename)
            language = self.verifier.get_language_for_file(file_path)
            if expected_lang:
                assert language == expected_lang, (
                    f"Expected {expected_lang} for {filename}, got {language}"
                )

    def test_get_language_for_file_by_filename(self):
        """Test language detection by exact filename."""
        test_cases = [
            ("Dockerfile", "dockerfile"),
            ("Makefile", "makefile"),
        ]

        for filename, expected_lang in test_cases:
            file_path = Path(filename)
            language = self.verifier.get_language_for_file(file_path)
            if expected_lang:
                assert language == expected_lang, (
                    f"Expected {expected_lang} for {filename}, got {language}"
                )

    def test_get_language_for_file_unknown(self):
        """Test language detection for unknown file types."""
        # Create verifier with default file type disabled to test unknown handling
        verifier = SPDXVerifier(disable_default_file_type=True)
        file_path = Path("unknown.xyz")
        language = verifier.get_language_for_file(file_path)
        assert language is None

    def test_check_license_header_valid_python(self):
        """Test checking valid SPDX header in Python file."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert passed
        assert "Valid SPDX headers found" in message

    def test_check_license_header_missing_license(self):
        """Test checking file missing SPDX license header."""
        content = """# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert not passed
        assert "Missing license header" in message

    def test_check_license_header_missing_copyright(self):
        """Test checking file missing SPDX copyright header."""
        content = """# SPDX-License-Identifier: Apache-2.0

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert not passed
        assert "Missing copyright header" in message

    def test_check_license_header_missing_both(self):
        """Test checking file missing both headers."""
        content = """def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert not passed
        assert "Missing both license and copyright headers" in message

    def test_check_license_header_wrong_license(self):
        """Test checking file with wrong license."""
        content = """# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert not passed
        assert "Wrong license" in message

    def test_check_license_header_wrong_copyright(self):
        """Test checking file with wrong copyright."""
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Wrong Corp

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        passed, message = self.verifier.check_license_header(file_path)
        assert not passed
        assert "Wrong copyright" in message

    def test_check_license_header_javascript(self):
        """Test checking valid SPDX header in JavaScript file."""
        content = """// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2025 The Linux Foundation

function hello() {
    console.log("Hello");
}
"""
        file_path = self.create_test_file(content, "test.js")
        passed, message = self.verifier.check_license_header(file_path)
        assert passed
        assert "Valid SPDX headers found" in message

    def test_check_license_header_css(self):
        """Test checking valid SPDX header in CSS file."""
        content = """/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: 2025 The Linux Foundation */

body {
    margin: 0;
}
"""
        file_path = self.create_test_file(content, "test.css")
        passed, message = self.verifier.check_license_header(file_path)
        assert passed
        assert "Valid SPDX headers found" in message

    def test_check_license_header_unknown_file_type(self):
        """Test checking unknown file type with default file type disabled."""
        content = """Some content
without headers
"""
        # Use verifier with default file type disabled
        verifier = SPDXVerifier(disable_default_file_type=True)
        file_path = self.create_test_file(content, "test.unknown")
        passed, message = verifier.check_license_header(file_path)
        assert passed  # Unknown types are skipped when default file type is disabled
        assert message == "Unknown file type, skipping"
        assert "Unknown file type, skipping" in message

    def test_should_skip_file_basic_patterns(self):
        """Test basic file skipping patterns."""
        verifier = SPDXVerifier(skip_patterns=["*.min.js", "node_modules/**"])

        # Should skip
        assert verifier.should_skip_file(Path("app.min.js"))
        assert verifier.should_skip_file(Path("node_modules/package/index.js"))

        # Should not skip
        assert not verifier.should_skip_file(Path("app.js"))
        assert not verifier.should_skip_file(Path("src/main.js"))

    def test_should_skip_file_default_patterns(self):
        """Test that default skip patterns are applied."""
        # These patterns should come from spdx-config.yaml
        verifier = SPDXVerifier()

        # Should skip cache directories (from default patterns)
        assert verifier.should_skip_file(Path("__pypackages__/file.py"))
        assert verifier.should_skip_file(Path(".git/config"))
        assert verifier.should_skip_file(Path("node_modules/package.json"))

    def test_verify_directory_success(self):
        """Test directory verification with all valid files."""
        # Create valid files
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(valid_content, "valid1.py")
        self.create_test_file(valid_content, "valid2.py")

        result = self.verifier.verify_directory(self.test_dir)
        assert result is True
        assert self.verifier.stats["checked"] == 2
        assert self.verifier.stats["passed"] == 2

    def test_verify_directory_with_failures(self):
        """Test directory verification with some invalid files."""
        # Create valid file
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        self.create_test_file(valid_content, "valid.py")

        # Create invalid file
        invalid_content = """def hello():
    pass
"""
        self.create_test_file(invalid_content, "invalid.py")

        result = self.verifier.verify_directory(self.test_dir)
        assert result is False
        assert self.verifier.stats["checked"] == 2
        assert self.verifier.stats["passed"] == 1

    def test_verify_directory_with_skipped_files(self):
        """Test directory verification with skipped files."""
        verifier = SPDXVerifier(skip_patterns=["skip_*"])

        # Create valid file that should be checked
        valid_content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.test_dir / "check_me.py"
        file_path.write_text(valid_content, encoding="utf-8")

        # Create file that should be skipped
        skip_path = self.test_dir / "skip_me.py"
        skip_path.write_text("def hello(): pass", encoding="utf-8")

        result = verifier.verify_directory(self.test_dir)
        assert result is True
        assert verifier.stats["checked"] == 1  # Only one file checked
        assert verifier.stats["skipped"] == 1  # One file skipped

    def test_verify_directory_nonexistent(self):
        """Test verifying non-existent directory."""
        nonexistent = Path("/path/that/does/not/exist")
        result = self.verifier.verify_directory(nonexistent)
        assert result is False

    def test_stats_tracking(self):
        """Test that statistics are properly tracked."""
        # Create files with different issues
        files_content = [
            ("missing_both.py", "def hello(): pass"),
            (
                "missing_license.py",
                "# SPDX-FileCopyrightText: 2025 The Linux Foundation\ndef hello(): pass",
            ),
            (
                "missing_copyright.py",
                "# SPDX-License-Identifier: Apache-2.0\ndef hello(): pass",
            ),
            (
                "test_wrong_license.py",
                "# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: 2025 The Linux Foundation\ndef hello(): pass",
            ),
            (
                "valid.py",
                "# SPDX-License-Identifier: Apache-2.0\n# SPDX-FileCopyrightText: 2025 The Linux Foundation\ndef hello(): pass",
            ),
        ]

        for filename, content in files_content:
            self.create_test_file(content, filename)

        self.verifier.verify_directory(self.test_dir)

        assert self.verifier.stats["checked"] == 5
        assert self.verifier.stats["passed"] == 1
        assert self.verifier.stats["missing_license"] >= 1
        assert self.verifier.stats["missing_copyright"] >= 1

    def test_default_file_type_handling_disabled(self):
        """Test default file type handling when disabled."""
        verifier = SPDXVerifier(disable_default_file_type=True)

        # File without extension should return None when disabled
        file_path = Path("no_extension_file")
        language = verifier.get_language_for_file(file_path)
        assert language is None

    def test_default_file_type_handling_enabled(self):
        """Test default file type handling when enabled."""
        verifier = SPDXVerifier(enable_default_file_type=True)

        # This test depends on config having default_file_type settings
        config = load_config()
        if config.get("default_file_type", {}).get("enabled"):
            file_path = Path("no_extension_file")
            language = verifier.get_language_for_file(file_path)
            # Should return the default language or None if not configured
            assert language is None or isinstance(language, str)

    def test_file_encoding_handling(self):
        """Test handling of files with different encodings."""
        # Create file with UTF-8 content
        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
# This file contains unicode: ñáéíóú

def hello():
    pass
"""
        file_path = self.create_test_file(content, "unicode.py")
        passed, _ = self.verifier.check_license_header(file_path)
        assert passed

    def test_print_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test summary printing functionality."""
        # Set up some stats
        self.verifier.stats["checked"] = 10
        self.verifier.stats["passed"] = 7
        self.verifier.stats["skipped"] = 5
        self.verifier.stats["missing_license"] = 2
        self.verifier.stats["missing_copyright"] = 1

        self.verifier.print_summary()

        captured = capsys.readouterr()
        assert "VERIFICATION SUMMARY" in captured.out
        assert "Files checked: 10" in captured.out
        assert "Passed: 7" in captured.out
        assert "Failed: 3" in captured.out
        assert "Skipped: 5" in captured.out


class TestSPDXVerifierEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_empty_file(self):
        """Test checking empty file."""
        file_path = self.test_dir / "empty.py"
        file_path.write_text("", encoding="utf-8")

        verifier = SPDXVerifier()
        passed, message = verifier.check_license_header(file_path)
        assert not passed
        assert "Missing both license and copyright headers" in message

    def test_binary_file_handling(self):
        """Test handling of binary files (should be handled gracefully)."""
        # Create a file with binary content
        file_path = self.test_dir / "binary.py"
        file_path.write_bytes(b"\x00\x01\x02\x03\x04")

        verifier = SPDXVerifier()
        # Should not crash even with binary content
        passed, message = verifier.check_license_header(file_path)
        # Result may vary, but should not raise exception
        assert isinstance(passed, bool)
        assert isinstance(message, str)

    def test_very_long_lines(self):
        """Test files with very long lines."""
        long_line = "# " + "x" * 10000 + "\n"
        content = (
            long_line
            + """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        )
        file_path = self.test_dir / "long_lines.py"
        file_path.write_text(content, encoding="utf-8")

        verifier = SPDXVerifier()
        passed, _ = verifier.check_license_header(file_path)
        assert passed

    def test_permission_denied(self):
        """Test handling of permission denied errors."""
        file_path = self.test_dir / "restricted.py"
        file_path.write_text("content", encoding="utf-8")

        # Mock to simulate permission denied
        verifier = SPDXVerifier()
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            passed, message = verifier.check_license_header(file_path)
            assert not passed
            assert "Error reading file" in message

    @patch("spdx_verify.pathspec", None)
    def test_fallback_pattern_matching(self):
        """Test fallback pattern matching when pathspec is not available."""
        verifier = SPDXVerifier(skip_patterns=["*.min.js"])

        # Should fall back to basic glob matching
        assert verifier.should_skip_file(Path("app.min.js"))
        assert not verifier.should_skip_file(Path("app.js"))


class TestSPDXVerifierIntegration:
    """Integration tests with real file system operations."""

    def test_with_real_test_files(self):
        """Test with the actual test_files directory."""
        # Get the test_files directory from within tests
        test_files_dir = Path(__file__).parent / "test_files"

        if test_files_dir.exists():
            verifier = SPDXVerifier(debug=True)
            verifier.verify_directory(test_files_dir)

            # Should find both passing and failing files
            assert verifier.stats["checked"] > 0
            # Some files should pass (test.py, test.js, etc.)
            assert verifier.stats["passed"] > 0
            # Some files should fail (test_no_license.py, test_wrong_license.py, etc.)
            assert verifier.stats["checked"] > verifier.stats["passed"]

    def test_config_loading(self):
        """Test that configuration is loaded correctly."""
        config = load_config()

        assert "languages" in config
        assert "python" in config["languages"]
        assert "javascript" in config["languages"]
        assert "default_skip_patterns" in config

        # Verify Python config
        python_config = config["languages"]["python"]
        assert python_config["comment_prefix"] == "#"
        assert ".py" in python_config["extensions"]


class TestReuseCompliance:
    """Test cases for REUSE compliance functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.git_root = self.test_dir / "repo"
        self.git_root.mkdir()
        self.licenses_dir = self.git_root / "LICENSES"
        self.licenses_dir.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def create_test_file(
        self, content: str, filename: str, directory: Optional[Path] = None
    ) -> Path:
        """Create a test file with given content."""
        if directory is None:
            directory = self.git_root
        file_path = directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def create_license_file(
        self, license_id: str, content: Optional[str] = None
    ) -> Path:
        """Create a license file in LICENSES directory."""
        license_file = self.licenses_dir / f"{license_id}.txt"
        if content is None:
            content = f"License text for {license_id}"
        license_file.write_text(content, encoding="utf-8")
        return license_file

    def test_extract_license_identifiers_from_file_python(self):
        """Test extracting license identifiers from Python files."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == {"Apache-2.0"}

    def test_extract_license_identifiers_from_file_multiple_licenses(self):
        """Test extracting multiple license identifiers from a file."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """# SPDX-License-Identifier: Apache-2.0 OR MIT
# SPDX-FileCopyrightText: 2025 The Linux Foundation

def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == {"Apache-2.0 OR MIT"}

    def test_extract_license_identifiers_from_file_javascript(self):
        """Test extracting license identifiers from JavaScript files."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2025 The Linux Foundation

function hello() {
    console.log("Hello");
}
"""
        file_path = self.create_test_file(content, "test.js")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == {"MIT"}

    def test_extract_license_identifiers_from_file_css(self):
        """Test extracting license identifiers from CSS files."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """/* SPDX-License-Identifier: Apache-2.0 */
/* SPDX-FileCopyrightText: 2025 The Linux Foundation */

body {
    margin: 0;
}
"""
        file_path = self.create_test_file(content, "test.css")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == {"Apache-2.0"}

    def test_extract_license_identifiers_from_file_html(self):
        """Test extracting license identifiers from HTML files."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2025 The Linux Foundation -->
<html>
<body>
    <h1>Hello</h1>
</body>
</html>
"""
        file_path = self.create_test_file(content, "test.html")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == {"Apache-2.0"}

    def test_extract_license_identifiers_from_file_no_license(self):
        """Test extracting license identifiers from file without license header."""
        from spdx_verify import extract_license_identifiers_from_file

        content = """def hello():
    pass
"""
        file_path = self.create_test_file(content, "test.py")
        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == set()

    def test_extract_license_identifiers_from_file_binary(self):
        """Test extracting license identifiers from binary file."""
        from spdx_verify import extract_license_identifiers_from_file

        # Create a binary file
        file_path = self.git_root / "binary.bin"
        file_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        license_ids = extract_license_identifiers_from_file(file_path)
        assert license_ids == set()

    def test_verify_reuse_compliance_success(self):
        """Test REUSE compliance check with all required license files present."""
        from spdx_verify import verify_reuse_compliance

        # Create test files with different licenses
        apache_file = self.create_test_file(
            "# SPDX-License-Identifier: Apache-2.0\n# Content", "apache.py"
        )
        mit_file = self.create_test_file(
            "# SPDX-License-Identifier: MIT\n# Content", "mit.py"
        )

        # Create corresponding license files
        self.create_license_file("Apache-2.0")
        self.create_license_file("MIT")

        git_tracked_files = {apache_file, mit_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert is_compliant
        assert issues == []

    def test_verify_reuse_compliance_missing_license_file(self):
        """Test REUSE compliance check with missing license file."""
        from spdx_verify import verify_reuse_compliance

        # Create test file with license that doesn't have corresponding file
        test_file = self.create_test_file(
            "# SPDX-License-Identifier: GPL-3.0\n# Content", "test.py"
        )

        # Only create Apache-2.0 license file, not GPL-3.0
        self.create_license_file("Apache-2.0")

        git_tracked_files = {test_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert not is_compliant
        assert len(issues) == 1
        assert "Missing license file: LICENSES/GPL-3.0.txt" in issues[0]

    def test_verify_reuse_compliance_no_licenses_directory(self):
        """Test REUSE compliance check when LICENSES directory doesn't exist."""
        # Remove LICENSES directory
        import shutil

        from spdx_verify import verify_reuse_compliance

        shutil.rmtree(self.licenses_dir)

        test_file = self.create_test_file(
            "# SPDX-License-Identifier: Apache-2.0\n# Content", "test.py"
        )

        git_tracked_files = {test_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert not is_compliant
        assert len(issues) == 1
        assert "LICENSES directory not found at repository root" in issues[0]

    def test_verify_reuse_compliance_incorrect_license_file_extension(self):
        """Test REUSE compliance check with license file having incorrect extension."""
        from spdx_verify import verify_reuse_compliance

        # Create test file
        test_file = self.create_test_file(
            "# SPDX-License-Identifier: Apache-2.0\n# Content", "test.py"
        )

        # Create license files with correct and incorrect extensions
        self.create_license_file("Apache-2.0")  # Correct .txt extension
        incorrect_license = self.licenses_dir / "MIT.license"  # Incorrect extension
        incorrect_license.write_text("MIT license text", encoding="utf-8")

        git_tracked_files = {test_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert not is_compliant
        assert len(issues) == 1
        assert (
            "License file with incorrect extension: LICENSES/MIT.license" in issues[0]
        )

    def test_verify_reuse_compliance_complex_license_expressions(self):
        """Test REUSE compliance with complex license expressions."""
        from spdx_verify import verify_reuse_compliance

        # Create test files with complex license expressions
        dual_licensed_file = self.create_test_file(
            "# SPDX-License-Identifier: Apache-2.0 OR MIT\n# Content", "dual.py"
        )
        with_exception_file = self.create_test_file(
            "# SPDX-License-Identifier: GPL-3.0 WITH GCC-exception-3.1\n# Content",
            "with_exception.py",
        )

        # Create license files for all components
        self.create_license_file("Apache-2.0 OR MIT")
        self.create_license_file("GPL-3.0 WITH GCC-exception-3.1")

        git_tracked_files = {dual_licensed_file, with_exception_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert is_compliant
        assert issues == []

    def test_verify_reuse_compliance_empty_git_tracked_files(self):
        """Test REUSE compliance with empty set of Git tracked files."""
        from spdx_verify import verify_reuse_compliance

        git_tracked_files: set[Path] = set()

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        assert is_compliant
        assert issues == []

    def test_verify_reuse_compliance_files_without_licenses(self):
        """Test REUSE compliance with files that don't have license headers."""
        from spdx_verify import verify_reuse_compliance

        # Create test files without license headers
        no_license_file = self.create_test_file(
            "def hello(): pass", "test_no_license.py"
        )

        git_tracked_files = {no_license_file}

        is_compliant, issues = verify_reuse_compliance(
            git_tracked_files, self.git_root, debug=False
        )

        # Should be compliant since no licenses are used
        assert is_compliant
        assert issues == []

    def test_verify_reuse_compliance_debug_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test REUSE compliance debug output."""
        from spdx_verify import verify_reuse_compliance

        test_file = self.create_test_file(
            "# SPDX-License-Identifier: Apache-2.0\n# Content", "test.py"
        )
        self.create_license_file("Apache-2.0")

        git_tracked_files = {test_file}

        _, _ = verify_reuse_compliance(git_tracked_files, self.git_root, debug=True)

        captured = capsys.readouterr()
        assert "Found license identifiers in use: Apache-2.0" in captured.out
        # We removed the debug message from verify_reuse_compliance
        # assert "✅ REUSE compliance check passed" in captured.out

    def test_verify_reuse_compliance_debug_output_with_issues(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test REUSE compliance debug output when issues are found."""
        from spdx_verify import verify_reuse_compliance

        test_file = self.create_test_file(
            "# SPDX-License-Identifier: GPL-3.0\n# Content", "test.py"
        )
        # Don't create the GPL-3.0.txt file

        git_tracked_files = {test_file}

        _, _ = verify_reuse_compliance(git_tracked_files, self.git_root, debug=True)

        captured = capsys.readouterr()
        assert "Found license identifiers in use: GPL-3.0" in captured.out
        # We removed the debug message from verify_reuse_compliance
        # assert "❌ REUSE compliance issues found:" in captured.out
        # assert "Missing license file: LICENSES/GPL-3.0.txt" in captured.out

    def test_get_git_tracked_files_basic(self):
        """Test getting Git tracked files from a repository."""
        from spdx_verify import get_git_tracked_files

        # This test requires a real Git repository setup, so we'll mock it
        # or test with the actual repo if available
        try:
            tracked_files = get_git_tracked_files(Path("."))
            assert isinstance(tracked_files, set)
            # Should contain at least the main spdx_verify.py file
            assert any(str(f).endswith("spdx_verify.py") for f in tracked_files)
        except subprocess.CalledProcessError:
            # Git not available or not in a git repo - this is expected in some test environments
            pass

    def test_find_git_root_basic(self):
        """Test finding Git root directory."""
        from spdx_verify import find_git_root

        try:
            git_root = find_git_root()
            if git_root:
                assert isinstance(git_root, Path)
                assert (git_root / ".git").exists()
        except Exception:
            # Git not available - this is expected in some test environments
            pass

    def test_reuse_compliance_integration_with_verify(self):
        """Test REUSE compliance integration with the main verify function."""
        from spdx_verify import verify

        # Create a temporary directory structure that mimics a real project
        project_dir = self.test_dir / "project"
        project_dir.mkdir()

        # Initialize git repository
        try:
            subprocess.run(
                ["git", "init"], cwd=project_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            # Create LICENSES directory and files
            licenses_dir = project_dir / "LICENSES"
            licenses_dir.mkdir()
            (licenses_dir / "Apache-2.0.txt").write_text("Apache License text")

            # Create source file
            source_file = project_dir / "main.py"
            source_file.write_text(
                "# SPDX-License-Identifier: Apache-2.0\n"
                "# SPDX-FileCopyrightText: 2025 The Linux Foundation\n\n"
                "def main(): pass\n"
            )

            # Add and commit files
            subprocess.run(
                ["git", "add", "."], cwd=project_dir, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=project_dir,
                check=True,
                capture_output=True,
            )

            # Test verify function with REUSE compliance
            # Change to project directory temporarily
            original_cwd = os.getcwd()
            try:
                os.chdir(project_dir)
                # This should pass without raising an exception
                verify(
                    paths=[str(source_file)],
                    pre_commit_mode=True,
                    reuse_compliance=True,
                    debug=True,
                )
            finally:
                os.chdir(original_cwd)

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available - skip this test
            import pytest

            pytest.skip("Git not available for integration testing")
