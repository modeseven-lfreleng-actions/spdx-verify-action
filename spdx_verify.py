#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
SPDX License Header Verification Tool

A comprehensive tool for verifying SPDX license headers in source code files.
Supports both CLI usage and GitHub Actions integration with configurable
language patterns and skip rules.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

import yaml

if TYPE_CHECKING:
    import pathspec
    import typer
else:
    try:
        import typer
    except ImportError:
        typer = None

    try:
        import pathspec  # type: ignore[import-not-found]
    except ImportError:
        pathspec = None  # type: ignore[assignment]

# Global configuration
CONFIG_FILE = "spdx-config.yaml"
DEFAULT_LICENSE = "Apache-2.0"
DEFAULT_COPYRIGHT = "The Linux Foundation"

# SPDX constants
SPDX_LICENSE_IDENTIFIER = "SPDX-License-Identifier:"
SPDX_FILE_COPYRIGHT = "SPDX-FileCopyrightText:"

# Comment style patterns
HASH_SPDX_LICENSE = f"# {SPDX_LICENSE_IDENTIFIER}"
HASH_SPDX_COPYRIGHT = f"# {SPDX_FILE_COPYRIGHT}"
SLASH_SPDX_LICENSE = f"// {SPDX_LICENSE_IDENTIFIER}"
SLASH_SPDX_COPYRIGHT = f"// {SPDX_FILE_COPYRIGHT}"
C_STYLE_SPDX_LICENSE = f"/* {SPDX_LICENSE_IDENTIFIER}"
C_STYLE_SPDX_COPYRIGHT = f"/* {SPDX_FILE_COPYRIGHT}"
HTML_SPDX_LICENSE = f"<!-- {SPDX_LICENSE_IDENTIFIER}"
HTML_SPDX_COPYRIGHT = f"<!-- {SPDX_FILE_COPYRIGHT}"


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def load_gitignore_patterns(directory: Path) -> List[str]:
    """Load patterns from .gitignore file in the given directory"""
    gitignore_path = directory / ".gitignore"
    patterns = []

    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        # Convert gitignore patterns to pathspec-compatible patterns
                        patterns.append(line)
        except (IOError, UnicodeDecodeError):
            # Silently ignore errors reading .gitignore
            pass

    return patterns


def load_config() -> Dict[str, Any]:
    """Load language configuration from YAML file"""
    config_path = Path(__file__).parent / CONFIG_FILE

    # Default configuration if file doesn't exist
    default_config = {
        "languages": {
            "python": {
                "extensions": [".py", ".pyx", ".pyi"],
                "comment_style": "hash",
                "patterns": [HASH_SPDX_LICENSE, HASH_SPDX_COPYRIGHT],
            },
            "javascript": {
                "extensions": [".js", ".jsx", ".ts", ".tsx"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "css": {
                "extensions": [".css", ".scss", ".sass", ".less"],
                "comment_style": "c_style",
                "patterns": [
                    C_STYLE_SPDX_LICENSE,
                    C_STYLE_SPDX_COPYRIGHT,
                ],
            },
            "html": {
                "extensions": [".html", ".xml", ".svg"],
                "comment_style": "html",
                "patterns": [
                    HTML_SPDX_LICENSE,
                    HTML_SPDX_COPYRIGHT,
                ],
            },
            "shell": {
                "extensions": [".sh", ".bash", ".zsh"],
                "comment_style": "hash",
                "patterns": [HASH_SPDX_LICENSE, HASH_SPDX_COPYRIGHT],
            },
            "c_cpp": {
                "extensions": [".c", ".cpp", ".h", ".hpp", ".cc", ".cxx"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "java": {
                "extensions": [".java"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "rust": {
                "extensions": [".rs"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "go": {
                "extensions": [".go"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "ruby": {
                "extensions": [".rb", ".rake"],
                "comment_style": "hash",
                "patterns": [HASH_SPDX_LICENSE, HASH_SPDX_COPYRIGHT],
            },
            "php": {
                "extensions": [".php"],
                "comment_style": "double_slash",
                "patterns": [
                    SLASH_SPDX_LICENSE,
                    SLASH_SPDX_COPYRIGHT,
                ],
            },
            "yaml": {
                "extensions": [".yml", ".yaml"],
                "comment_style": "hash",
                "patterns": [HASH_SPDX_LICENSE, HASH_SPDX_COPYRIGHT],
            },
            "dockerfile": {
                "extensions": ["Dockerfile", "dockerfile"],
                "comment_style": "hash",
                "patterns": [HASH_SPDX_LICENSE, HASH_SPDX_COPYRIGHT],
            },
            "makefile": {
                "extensions": ["Makefile", "makefile", ".mk"],
                "comment_style": "hash",
                "patterns": ["# SPDX-License-Identifier:", "# SPDX-FileCopyrightText:"],
            },
            "markdown": {
                "extensions": [".md", ".markdown"],
                "comment_style": "html",
                "patterns": [
                    "<!-- SPDX-License-Identifier:",
                    "<!-- SPDX-FileCopyrightText:",
                ],
            },
        },
        "default_skip_patterns": [
            "*.min.js",
            "*.min.css",
            "node_modules/**",
            ".git/**",
            "__pycache__/**",
            "__pypackages__/**",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".pytest_cache/**",
            ".mypy_cache/**",
            ".DS_Store",
            "*.log",
            "*.egg-info/**",
            "dist/**",
            "build/**",
            ".venv/**",
            "venv/**",
        ],
    }

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f) or {}
                # Merge loaded config with default config
                merged_config = default_config.copy()
                if loaded_config:
                    merged_config.update(loaded_config)
                return merged_config
        except (yaml.YAMLError, IOError, Exception) as e:
            print(
                f"{Colors.YELLOW}Warning: Could not load config file: {e}{Colors.END}"
            )
            return default_config

    return default_config


class SPDXVerifier:
    """Main SPDX license header verification class"""

    def __init__(
        self,
        license_id: str = DEFAULT_LICENSE,
        copyright_holder: str = DEFAULT_COPYRIGHT,
        skip_patterns: Optional[List[str]] = None,
        debug: bool = False,
        disable_default_file_type: bool = False,
        enable_default_file_type: bool = False,
        default_file_type_override: Optional[str] = None,
        directory: Optional[Path] = None,
    ):
        self.license_id = license_id
        self.copyright_holder = copyright_holder
        self.debug = debug
        self.disable_default_file_type = disable_default_file_type
        self.enable_default_file_type = enable_default_file_type
        self.default_file_type_override = default_file_type_override
        self.config = load_config()

        # Merge user-provided skip patterns with default ones from config
        self.skip_patterns = skip_patterns or []
        default_skip_patterns = self.config.get("default_skip_patterns", [])

        # Load .gitignore patterns from current working directory if not specified
        work_dir = directory or Path.cwd()
        gitignore_patterns = load_gitignore_patterns(work_dir)

        # Combine default patterns, gitignore patterns, and user patterns, removing duplicates
        all_skip_patterns = list(
            set(default_skip_patterns + gitignore_patterns + self.skip_patterns)
        )
        self.skip_patterns = all_skip_patterns

        if self.debug and gitignore_patterns:
            print(
                f"{Colors.CYAN}📁 Loaded {len(gitignore_patterns)} patterns from .gitignore{Colors.END}"
            )

        # Build extension to language mapping
        self.ext_to_lang: Dict[str, str] = {}
        self.filename_to_lang: Dict[str, str] = {}

        for lang_name, lang_config in self.config["languages"].items():
            # Process extensions if present
            if "extensions" in lang_config:
                for ext in lang_config["extensions"]:
                    self.ext_to_lang[ext.lower()] = lang_name

            # Process filenames if present
            if "filenames" in lang_config:
                for filename in lang_config["filenames"]:
                    self.filename_to_lang[filename.lower()] = lang_name

            # Warn if neither extensions nor filenames are defined
            if "extensions" not in lang_config and "filenames" not in lang_config:
                if self.debug:
                    print(
                        f"{Colors.YELLOW}Warning: Language config for '{lang_name}' missing both 'extensions' and 'filenames' keys, skipping.{Colors.END}"
                    )

        # Statistics
        self.stats = {
            "checked": 0,
            "passed": 0,
            "missing_license": 0,
            "missing_copyright": 0,
            "wrong_license": 0,
            "wrong_copyright": 0,
            "skipped": 0,
        }

        # Compile skip patterns
        self.pathspec_matcher = None
        if pathspec and self.skip_patterns:
            try:
                self.pathspec_matcher = pathspec.PathSpec.from_lines(
                    "gitwildmatch", self.skip_patterns
                )
            except Exception as e:
                if self.debug:
                    print(
                        f"{Colors.YELLOW}Warning: Could not compile pathspec patterns: {e}{Colors.END}"
                    )

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on patterns"""
        # Convert to string for pattern matching
        path_str = str(file_path)
        relative_path = file_path.name

        # Use pathspec if available
        if self.pathspec_matcher:
            return bool(self.pathspec_matcher.match_file(path_str)) or bool(
                self.pathspec_matcher.match_file(relative_path)
            )

        # Fallback to basic glob matching
        for pattern in self.skip_patterns:
            if self._glob_match(path_str, pattern) or self._glob_match(
                relative_path, pattern
            ):
                return True
        return False

    def _glob_match(self, path: str, pattern: str) -> bool:
        """Simple glob pattern matching fallback"""
        try:
            # Simple wildcard matching
            if "*" in pattern:
                import fnmatch

                return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
                    Path(path).name, pattern
                )
            else:
                return pattern in path or pattern == Path(path).name
        except Exception:
            return False

    def get_language_for_file(self, file_path: Path) -> Optional[str]:
        """Determine the language configuration for a file"""
        # Check by extension first
        suffix = file_path.suffix.lower()
        if suffix in self.ext_to_lang:
            return self.ext_to_lang[suffix]

        # Check by exact filename (for files like Dockerfile, Makefile)
        name = file_path.name
        if name.lower() in self.filename_to_lang:
            return self.filename_to_lang[name.lower()]

        # Fallback: check if filename matches any extension pattern (legacy behavior)
        for ext, lang in self.ext_to_lang.items():
            if name.lower() == ext.lower() or name.lower().endswith(ext.lower()):
                if self.debug:
                    print(
                        f"{Colors.CYAN}Debug: File {file_path} matched extension pattern '{ext}' -> language '{lang}'{Colors.END}"
                    )
                return lang

        # Check for default file type handling
        should_use_default = False

        if self.enable_default_file_type:
            # Explicitly enabled via CLI
            should_use_default = True
        elif not self.disable_default_file_type:
            # Check config setting (default behavior)
            default_config = self.config.get("default_file_type", {})
            should_use_default = default_config.get("enabled", False)

        if should_use_default:
            # Determine which language to use
            default_lang = None
            if self.default_file_type_override:
                # Use CLI override
                default_lang = self.default_file_type_override
                if self.debug:
                    print(
                        f"{Colors.CYAN}Debug: Using CLI override file type '{default_lang}' for {file_path}{Colors.END}"
                    )
            else:
                # Use config default
                default_config = self.config.get("default_file_type", {})
                default_lang = default_config.get("language")
                if self.debug and default_lang:
                    print(
                        f"{Colors.CYAN}Debug: Using default file type '{default_lang}' for {file_path}{Colors.END}"
                    )

            # Validate the language exists in config
            if default_lang and default_lang in self.config.get("languages", {}):
                return default_lang
            elif default_lang:
                if self.debug:
                    print(
                        f"{Colors.YELLOW}Warning: Default file type '{default_lang}' not found in language configuration{Colors.END}"
                    )
        else:
            if self.debug:
                print(
                    f"{Colors.CYAN}Debug: Default file type handling disabled for {file_path}{Colors.END}"
                )

        return None

    def check_license_header(self, file_path: Path) -> Tuple[bool, str]:
        """Check if file has correct SPDX license header"""
        lang = self.get_language_for_file(file_path)
        if not lang:
            return True, "Unknown file type, skipping"

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                first_lines = content.split("\n")[:10]  # Check first 10 lines

                license_found = False
                copyright_found = False
                correct_license = False
                correct_copyright = False

                for line in first_lines:
                    line = line.strip()

                    # Check for license identifier
                    if "SPDX-License-Identifier:" in line:
                        license_found = True
                        if self.license_id in line:
                            correct_license = True

                    # Check for copyright
                    if "SPDX-FileCopyrightText:" in line:
                        copyright_found = True
                        if self.copyright_holder in line:
                            correct_copyright = True

                # Determine result
                if not license_found and not copyright_found:
                    return False, "Missing both license and copyright headers"
                elif not license_found:
                    return False, "Missing license header"
                elif not copyright_found:
                    return False, "Missing copyright header"
                elif not correct_license and not correct_copyright:
                    return (
                        False,
                        f"Wrong license and copyright (expected {self.license_id} and {self.copyright_holder})",
                    )
                elif not correct_license:
                    return False, f"Wrong license (expected {self.license_id})"
                elif not correct_copyright:
                    return False, f"Wrong copyright (expected {self.copyright_holder})"
                else:
                    return True, "Valid SPDX headers found"

        except (IOError, UnicodeDecodeError) as e:
            return False, f"Error reading file: {e}"

    def verify_directory(
        self, directory: Path, git_tracked_files: Optional[Set[Path]] = None
    ) -> bool:
        """Verify all files in a directory recursively"""
        if not directory.exists():
            print(
                f"{Colors.RED}Error: Directory {directory} does not exist{Colors.END}"
            )
            return False

        all_passed = True

        if self.debug:
            print(f"{Colors.BLUE}🔍 Scanning directory: {directory}{Colors.END}")
            print(f"{Colors.CYAN}License: {self.license_id}{Colors.END}")
            print(f"{Colors.CYAN}Copyright: {self.copyright_holder}{Colors.END}")
            if self.skip_patterns:
                print(
                    f"{Colors.CYAN}Skip patterns: {', '.join(self.skip_patterns)}{Colors.END}"
                )
            print()

        # Get all files recursively
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # If git_tracked_files is provided, only check tracked files
                if (
                    git_tracked_files is not None
                    and file_path.resolve() not in git_tracked_files
                ):
                    if self.debug:
                        relative_path = file_path.relative_to(directory)
                        print(
                            f"{Colors.YELLOW}⏩ SKIP: {relative_path} (not Git tracked){Colors.END}"
                        )
                    continue

                relative_path = file_path.relative_to(directory)

                # Check if file should be skipped
                if self.should_skip_file(relative_path):
                    self.stats["skipped"] += 1
                    if self.debug:
                        print(f"{Colors.YELLOW}⏩ SKIP: {relative_path}{Colors.END}")
                    continue

                # Check if we can handle this file type
                lang = self.get_language_for_file(file_path)
                if not lang:
                    self.stats["skipped"] += 1
                    if self.debug:
                        print(
                            f"{Colors.YELLOW}⏩ SKIP: {relative_path} (unknown file type){Colors.END}"
                        )
                    continue

                # Verify the file
                passed, message = self.check_license_header(file_path)
                self.stats["checked"] += 1

                if passed:
                    self.stats["passed"] += 1
                    if self.debug:
                        print(f"{Colors.GREEN}✅ PASS: {relative_path}{Colors.END}")
                else:
                    all_passed = False
                    if "Missing" in message:
                        if "license" in message.lower():
                            self.stats["missing_license"] += 1
                        if "copyright" in message.lower():
                            self.stats["missing_copyright"] += 1
                    elif "Wrong" in message:
                        if "license" in message.lower():
                            self.stats["wrong_license"] += 1
                        if "copyright" in message.lower():
                            self.stats["wrong_copyright"] += 1

                    print(
                        f"{Colors.RED}❌ FAIL: {relative_path} - {message}{Colors.END}"
                    )

        return all_passed

    def print_summary(self) -> None:
        """Print verification summary"""
        print(f"\n{Colors.BOLD}📊 VERIFICATION SUMMARY{Colors.END}")
        print(f"{Colors.CYAN}Files checked: {self.stats['checked']}{Colors.END}")
        print(f"{Colors.GREEN}Passed: {self.stats['passed']}{Colors.END}")
        print(
            f"{Colors.RED}Failed: {self.stats['checked'] - self.stats['passed']}{Colors.END}"
        )
        print(f"{Colors.YELLOW}Skipped: {self.stats['skipped']}{Colors.END}")

        if self.stats["missing_license"] > 0:
            print(
                f"{Colors.RED}Missing license: {self.stats['missing_license']}{Colors.END}"
            )
        if self.stats["missing_copyright"] > 0:
            print(
                f"{Colors.RED}Missing copyright: {self.stats['missing_copyright']}{Colors.END}"
            )
        if self.stats["wrong_license"] > 0:
            print(
                f"{Colors.RED}Wrong license: {self.stats['wrong_license']}{Colors.END}"
            )
        if self.stats["wrong_copyright"] > 0:
            print(
                f"{Colors.RED}Wrong copyright: {self.stats['wrong_copyright']}{Colors.END}"
            )


def find_git_root(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Find the Git repository root directory.

    Args:
        start_path: Path to start searching from

    Returns:
        Path to Git root directory, or None if not in a Git repository
    """
    current_path = start_path.resolve()

    while current_path != current_path.parent:
        if (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent

    return None


def extract_license_identifiers_from_file(file_path: Path) -> Set[str]:
    """
    Extract all SPDX license identifiers from a file.

    Args:
        file_path: Path to the file to extract license identifiers from

    Returns:
        Set of license identifiers found in the file
    """
    license_ids: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            first_lines = content.split("\n")[:20]  # Check first 20 lines

            for line in first_lines:
                line = line.strip()
                if SPDX_LICENSE_IDENTIFIER in line:
                    # Extract the license identifier
                    parts = line.split(SPDX_LICENSE_IDENTIFIER)
                    if len(parts) > 1:
                        license_part = parts[1].strip()
                        # Remove comment characters and whitespace
                        license_part = (
                            license_part.replace("-->", "").replace("*/", "").strip()
                        )
                        license_ids.add(license_part)

    except (IOError, UnicodeDecodeError):
        pass  # Ignore files that can't be read

    return license_ids


def verify_reuse_compliance(
    git_tracked_files: Set[Path], git_root: Path, debug: bool = False
) -> Tuple[bool, List[str]]:
    """
    Verify REUSE compliance by checking that all license identifiers used in files
    have corresponding license files in the LICENSES directory.

    Args:
        git_tracked_files: Set of Git-tracked file paths
        git_root: Path to the Git repository root
        debug: Enable debug output

    Returns:
        Tuple of (is_compliant, list_of_issues)
    """
    licenses_dir = git_root / "LICENSES"
    if not licenses_dir.exists():
        return False, ["LICENSES directory not found at repository root"]

    # Collect all license identifiers used in tracked files
    used_licenses: Set[str] = set()
    for file_path in git_tracked_files:
        if file_path.is_file():
            file_licenses = extract_license_identifiers_from_file(file_path)
            used_licenses.update(file_licenses)

    if debug:
        print(
            f"{Colors.CYAN}Found license identifiers in use: {', '.join(sorted(used_licenses))}{Colors.END}"
        )

    # Check that each used license has a corresponding .txt file in LICENSES/
    issues: List[str] = []
    for license_id in used_licenses:
        license_file = licenses_dir / f"{license_id}.txt"
        if not license_file.exists():
            issues.append(f"Missing license file: LICENSES/{license_id}.txt")

    # Check for any license files that don't have .txt extension
    if licenses_dir.exists():
        for license_file in licenses_dir.iterdir():
            if license_file.is_file() and not license_file.name.endswith(".txt"):
                issues.append(
                    f"License file with incorrect extension: LICENSES/{license_file.name} (should be .txt)"
                )

    return len(issues) == 0, issues


def get_git_tracked_files(repo_path: Path = Path(".")) -> Set[Path]:
    """
    Get a set of files tracked by Git in the specified repository.

    Args:
        repo_path: Path to the Git repository root

    Returns:
        Set of absolute paths to files tracked by Git

    Raises:
        subprocess.CalledProcessError: If git command fails
        FileNotFoundError: If git is not available
    """
    try:
        # Run git ls-files to get tracked files
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Convert relative paths to absolute paths
        git_files: Set[Path] = set()
        for file_path in result.stdout.strip().split("\n"):
            if file_path:  # Skip empty lines
                absolute_path = (repo_path / file_path).resolve()
                git_files.add(absolute_path)

        return git_files

    except subprocess.CalledProcessError as e:
        print(
            f"{Colors.RED}Error: Failed to get Git tracked files: {e.stderr.strip()}{Colors.END}"
        )
        raise
    except FileNotFoundError:
        print(f"{Colors.RED}Error: Git is not available or not in PATH{Colors.END}")
        raise


def is_github_actions() -> bool:
    """Check if running in GitHub Actions environment"""
    return os.getenv("GITHUB_ACTIONS") == "true"


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output"""
    if is_github_actions():
        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            try:
                with open(github_output, "a", encoding="utf-8") as f:
                    f.write(f"{name}={value}\n")
            except IOError:
                pass


def verify(
    paths: List[str],
    license: str = DEFAULT_LICENSE,
    copyright_holder: str = DEFAULT_COPYRIGHT,
    skip: Optional[str] = None,
    debug: bool = False,
    disable_default_file_type: bool = False,
    enable_default_file_type: bool = False,
    default_file_type_override: Optional[str] = None,
    pre_commit_mode: bool = False,
    reuse_compliance: bool = False,
) -> None:
    """
    Verify SPDX license headers in the specified paths.

    Args:
        paths: List of file or directory paths to verify
        license: Expected SPDX license identifier
        copyright_holder: Expected copyright holder
        skip: Comma-separated list of skip patterns
        debug: Enable debug output
        disable_default_file_type: Disable default file type handling
        enable_default_file_type: Enable default file type handling
        default_file_type_override: Override default file type language
        pre_commit_mode: Only check files tracked by Git (for pre-commit hooks)
        reuse_compliance: Check REUSE compliance (only applies in pre-commit mode)
    """
    if debug:
        print(
            f"{Colors.CYAN}Debug: disable_default_file_type = {disable_default_file_type}{Colors.END}"
        )

    if not paths:
        paths = ["."]

    # Get Git tracked files if in pre-commit mode
    git_tracked_files = None
    if pre_commit_mode:
        if debug:
            print(
                f"{Colors.CYAN}Pre-commit mode: Only checking Git-tracked files{Colors.END}"
            )
        try:
            git_tracked_files = get_git_tracked_files()
            if debug:
                print(
                    f"{Colors.CYAN}Found {len(git_tracked_files)} Git-tracked files{Colors.END}"
                )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if debug:
                print(
                    f"{Colors.YELLOW}Warning: Could not get Git tracked files, checking all files: {e}{Colors.END}"
                )
            # Fall back to checking all files if Git fails

    # Parse skip patterns
    skip_patterns = []
    if skip:
        skip_patterns = [
            pattern.strip() for pattern in skip.split(",") if pattern.strip()
        ]

    # Determine the working directory for .gitignore loading
    # Use the first path to determine working directory, defaulting to current directory
    work_dir = Path.cwd()
    if paths:
        first_path = Path(paths[0])
        if first_path.is_dir():
            # For directory paths, use the current working directory for .gitignore
            # This ensures we use the project root .gitignore, not subdirectory ones
            work_dir = Path.cwd()
        elif first_path.is_file():
            work_dir = first_path.parent
        else:
            # Path might not exist yet or be relative, try to resolve it
            try:
                resolved_path = first_path.resolve()
                if resolved_path.is_dir():
                    # Still use current working directory for .gitignore
                    work_dir = Path.cwd()
                elif resolved_path.parent.exists():
                    work_dir = resolved_path.parent
            except (OSError, RuntimeError):
                # Keep current directory as fallback
                pass

    # Create verifier
    verifier = SPDXVerifier(
        license_id=license,
        copyright_holder=copyright_holder,
        skip_patterns=skip_patterns,
        debug=debug,
        disable_default_file_type=disable_default_file_type,
        enable_default_file_type=enable_default_file_type,
        default_file_type_override=default_file_type_override,
        directory=work_dir,
    )

    # If pre-commit mode is enabled, filter paths to only Git-tracked files
    git_tracked_files = None
    if pre_commit_mode:
        try:
            git_tracked_files = get_git_tracked_files()
            if debug:
                print(
                    f"{Colors.CYAN}Pre-commit mode: Only checking Git-tracked files{Colors.END}"
                )
                print(
                    f"{Colors.CYAN}Found {len(git_tracked_files)} Git-tracked files{Colors.END}"
                )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(
                f"{Colors.RED}Error: Could not get Git-tracked files for pre-commit mode{Colors.END}"
            )
            print(f"{Colors.RED}Falling back to checking all files{Colors.END}")
            if debug:
                print(f"{Colors.RED}Git error: {e}{Colors.END}")
            git_tracked_files = None

    # Verify all paths
    all_passed = True
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            # Single file verification
            # In pre-commit mode, skip files not tracked by Git
            if (
                git_tracked_files is not None
                and path.resolve() not in git_tracked_files
            ):
                if debug:
                    print(
                        f"{Colors.YELLOW}⏩ SKIP: {path} (not Git tracked){Colors.END}"
                    )
                continue

            # Check if file should be skipped
            if verifier.should_skip_file(path):
                verifier.stats["skipped"] += 1
                if debug:
                    print(f"{Colors.YELLOW}⏩ SKIP: {path}{Colors.END}")
                continue

            # Check if we can handle this file type
            lang = verifier.get_language_for_file(path)
            if not lang:
                verifier.stats["skipped"] += 1
                if debug:
                    print(
                        f"{Colors.YELLOW}⏩ SKIP: {path} (unknown file type){Colors.END}"
                    )
                continue

            passed, message = verifier.check_license_header(path)
            verifier.stats["checked"] += 1
            if passed:
                verifier.stats["passed"] += 1
                if debug:
                    print(f"{Colors.GREEN}✅ PASS: {path}{Colors.END}")
            else:
                all_passed = False
                print(f"{Colors.RED}❌ FAIL: {path} - {message}{Colors.END}")
        elif path.is_dir():
            # Directory verification
            if not verifier.verify_directory(path, git_tracked_files):
                all_passed = False
        else:
            print(f"{Colors.RED}Error: Path {path} does not exist{Colors.END}")
            all_passed = False

    # Run REUSE compliance check if enabled and in pre-commit mode
    if reuse_compliance and pre_commit_mode and git_tracked_files:
        if debug:
            print(f"{Colors.CYAN}Running REUSE compliance check...{Colors.END}")

        git_root = find_git_root()
        if git_root:
            reuse_passed, reuse_issues = verify_reuse_compliance(
                git_tracked_files, git_root, debug
            )
            if not reuse_passed:
                all_passed = False
                print(
                    f"{Colors.RED}❌ Repository REUSE compliance check failed{Colors.END}"
                )
                if debug:
                    for issue in reuse_issues:
                        print(f"{Colors.RED}  - {issue}{Colors.END}")
            else:
                print(
                    f"{Colors.GREEN}✅ Repository REUSE compliance check passed{Colors.END}"
                )
        else:
            print(
                f"{Colors.YELLOW}Warning: Could not find Git root for REUSE compliance check{Colors.END}"
            )

    # Print summary
    verifier.print_summary()

    # Set GitHub Actions outputs
    if is_github_actions():
        set_github_output("passed", str(all_passed).lower())
        set_github_output("files_checked", str(verifier.stats["checked"]))
        set_github_output("files_passed", str(verifier.stats["passed"]))
        set_github_output(
            "files_failed", str(verifier.stats["checked"] - verifier.stats["passed"])
        )

    # Exit with appropriate code
    if not all_passed:
        sys.exit(1)


def main() -> None:
    """Main entry point for CLI usage"""
    if is_github_actions():
        # GitHub Actions mode - use environment variables
        license_id = os.getenv("INPUT_LICENSE", DEFAULT_LICENSE)
        copyright_holder = os.getenv("INPUT_COPYRIGHT", DEFAULT_COPYRIGHT)
        paths_str = os.getenv("INPUT_PATHS", ".")
        skip_str = os.getenv("INPUT_SKIP", "")
        debug_str = os.getenv("INPUT_DEBUG", "false")
        pre_commit_mode_str = os.getenv("INPUT_PRE_COMMIT_MODE", "false")
        reuse_compliance_str = os.getenv("INPUT_REUSE_COMPLIANCE", "false")

        paths = [p.strip() for p in paths_str.split(",") if p.strip()]

        verify(
            paths=paths,
            license=license_id,
            copyright_holder=copyright_holder,
            skip=skip_str if skip_str else None,
            debug=debug_str.lower() == "true",
            pre_commit_mode=pre_commit_mode_str.lower() == "true",
            reuse_compliance=reuse_compliance_str.lower() == "true",
        )

    elif typer:
        # Use typer for rich CLI if available
        app = typer.Typer(help="SPDX License Header Verification Tool")

        @app.command()
        def cli(
            paths: Optional[List[str]] = typer.Argument(
                None, help="Paths to verify (files or directories)"
            ),
            license: str = typer.Option(
                DEFAULT_LICENSE,
                "--license",
                "-l",
                help="Expected SPDX license identifier",
            ),
            copyright_holder: str = typer.Option(
                DEFAULT_COPYRIGHT, "--copyright", "-c", help="Expected copyright holder"
            ),
            skip: Optional[str] = typer.Option(
                None, "--skip", "-s", help="Comma-separated skip patterns"
            ),
            debug: bool = typer.Option(
                False, "--debug", "-d", help="Enable debug output"
            ),
            disable_default_file_type: bool = typer.Option(
                False,
                "--disable-default-file-type",
                help="Disable default file type handling",
            ),
            enable_default_file_type: bool = typer.Option(
                False,
                "--enable-default-file-type",
                help="Enable default file type handling",
            ),
            default_file_type: Optional[str] = typer.Option(
                None, "--default-file-type", help="Override default file type language"
            ),
            pre_commit_mode: bool = typer.Option(
                False,
                "--pre-commit-mode",
                help="Only check files tracked by Git (for pre-commit hooks)",
            ),
            reuse_compliance: bool = typer.Option(
                False,
                "--reuse-compliance",
                help="Check REUSE compliance (only applies in pre-commit mode)",
            ),
        ) -> None:
            """Verify SPDX license headers in source code files."""
            if paths is None:
                paths = ["."]
            verify(
                paths,
                license,
                copyright_holder,
                skip,
                debug,
                disable_default_file_type,
                enable_default_file_type,
                default_file_type,
                pre_commit_mode,
                reuse_compliance,
            )

        app()

    else:
        # Fallback to argparse if typer not available
        parser = argparse.ArgumentParser(
            description="SPDX License Header Verification Tool"
        )
        parser.add_argument(
            "paths",
            nargs="*",
            default=["."],
            help="Paths to verify (files or directories)",
        )
        parser.add_argument(
            "--license",
            "-l",
            default=DEFAULT_LICENSE,
            help=f"Expected SPDX license identifier (default: {DEFAULT_LICENSE})",
        )
        parser.add_argument(
            "--copyright",
            "-c",
            default=DEFAULT_COPYRIGHT,
            help=f"Expected copyright holder (default: {DEFAULT_COPYRIGHT})",
        )
        parser.add_argument("--skip", "-s", help="Comma-separated skip patterns")
        parser.add_argument(
            "--debug", "-d", action="store_true", help="Enable debug output"
        )
        parser.add_argument(
            "--disable-default-file-type",
            action="store_true",
            help="Disable default file type handling",
        )
        parser.add_argument(
            "--enable-default-file-type",
            action="store_true",
            help="Enable default file type handling",
        )
        parser.add_argument(
            "--default-file-type", type=str, help="Override default file type language"
        )
        parser.add_argument(
            "--pre-commit-mode",
            action="store_true",
            help="Only check files tracked by Git (for pre-commit hooks)",
        )
        parser.add_argument(
            "--reuse-compliance",
            action="store_true",
            help="Check REUSE compliance (only applies in pre-commit mode)",
        )

        args = parser.parse_args()
        verify(
            paths=args.paths,
            license=args.license,
            copyright_holder=args.copyright,
            skip=args.skip,
            debug=args.debug,
            disable_default_file_type=args.disable_default_file_type,
            enable_default_file_type=args.enable_default_file_type,
            default_file_type_override=args.default_file_type,
            pre_commit_mode=args.pre_commit_mode,
            reuse_compliance=args.reuse_compliance,
        )


if __name__ == "__main__":
    main()
