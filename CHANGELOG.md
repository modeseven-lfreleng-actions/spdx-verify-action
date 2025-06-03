<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2025 The Linux Foundation -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-29

### Added

- Clean room implementation of SPDX license header verification
- Dual CLI/GitHub Actions support using Typer library
- External YAML configuration for language definitions
- Support for 15+ programming languages and file types
- Pattern-based file skipping with glob support
- Debug mode with visual indicators (✅ ❌ ⏩)
- Comprehensive error handling and exit codes
- Type hints and MyPy compatibility
- Extensive documentation and examples

### Features

- **Multi-language support**: Python, JavaScript, TypeScript, CSS, HTML,
  Shell, C/C++, Java, Rust, Go, Ruby, PHP, YAML, Dockerfile, Makefile
- **Flexible configuration**: External YAML file for easy customization
- **GitHub Actions integration**: Direct support with environment variables
- **CLI tool**: Standalone command-line interface with rich options
- **Smart license detection**: Distinguishes between missing and incorrect licenses
- **Pattern matching**: Intelligent file filtering with gitignore-style patterns

### GitHub Actions Inputs

- `directory`: Directory to scan (default: current directory)
- `license`: SPDX license identifier to verify (default: Apache-2.0)
- `skip`: Comma-separated patterns to skip
- `debug`: Enable debug output

### CLI Options

- `--license, -l`: Specify license to verify
- `--skip, -s`: Add skip patterns (repeatable)
- `--config, -c`: Custom configuration file
- `--debug, -d`: Enable debug mode
- `--no-default-skip`: Disable default skip patterns

### Exit Codes

- `0`: Success - all files have correct headers
- `1`: Missing headers - some files need attention
- `2`: Error - configuration or runtime issue
