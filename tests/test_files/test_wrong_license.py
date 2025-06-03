# SPDX-License-Identifier: MIT

"""
Test Python file with WRONG SPDX license header.
This should be detected as having MIT instead of Apache-2.0.
"""


def wrong_license() -> str:
    """Function in file with wrong license header."""
    return "This file has MIT license instead of Apache-2.0"
