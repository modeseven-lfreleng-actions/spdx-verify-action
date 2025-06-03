<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2025 The Linux Foundation -->

# Contributing to SPDX License Header Verification Action

We welcome contributions to this project! Here's how you can help:

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/lfreleng-actions/spdx-verify-action.git
   cd spdx-verify-action
   ```

2. Install dependencies:

   ```bash
   pip install pdm
   pdm install
   ```

3. Run tests:

   ```bash
   bash test_script.sh
   ```

## Adding Support for New Languages

To add support for a new programming language:

1. Edit `spdx-config.yaml` and add the language configuration:

   ```yaml
   languages:
     your_language:
       comment_prefix: "#"  # or "//" or "/*"
       comment_suffix: "*/"  # only for multi-line comments
       extensions:
         - .ext1
         - .ext2
       filenames:  # optional, for files without extensions
         - SpecialFile
   ```

2. Test the new language support:

   ```bash
   python spdx_verify.py your_test_files --debug
   ```

## Code Style

- Follow PEP 8 for Python code
- Add type hints for all functions
- Include docstrings for classes and methods
- Ensure all files have SPDX license headers

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Commit with a descriptive message
7. Push to your fork
8. Submit a pull request

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)

Thank you for contributing!
